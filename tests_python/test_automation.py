from __future__ import annotations
import asyncio
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from playwright.async_api import async_playwright
from pastehappy.browser import BrowserManager
from pastehappy.facebook import AutomationError, answer_membership_form, membership_answer, prepare_composer, join_group
from pastehappy.queue_store import QueueStore
from pastehappy.worker import QueueWorker

class MembershipTests(unittest.TestCase):
    def test_answer_specificity_and_unknown(self):
        answers = [{"question": "agree", "answer": "I agree"}, {"question": "agree to rules", "answer": "Yes"}]
        self.assertEqual(membership_answer("Do you AGREE to rules?", answers), "Yes")
        self.assertIsNone(membership_answer("Where do you live?", answers))
        self.assertIsNone(membership_answer("Agree?", [{"question":"agree", "answer":"Yes"}, {"question":"agree", "answer":"No"}]))

class WorkerTests(unittest.IsolatedAsyncioTestCase):
    async def test_timeout_skips_and_continues_with_stop_on_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            store = QueueStore(Path(directory)/'queue.json').init()
            store.import_rows([{"groupName": str(i), "groupUrl": f"https://facebook.com/groups/{i}", "postText":"Hello"} for i in range(2)])
            class Browser:
                calls = 0
                async def post_job(self, job, on_step, **options):
                    self.calls += 1
                    if self.calls == 1: raise AutomationError('COMPOSER_NOT_FOUND', 'Timeout')
                    return {"status":"posted"}
            browser = Browser()
            worker = QueueWorker(store=store, browser=browser, default_job_delay=0, max_jobs_per_run=2)
            worker.options = {"maxJobs":2, "delayMs":0, "cooldownMs":0, "stopOnFailure":True, "stopOnCheckpoint":True, "joinBeforePost":True, "composerTimeoutMs":1000, "membershipAnswers":[], "acceptGroupRules":True}
            worker.mode = 'running'
            with patch('pastehappy.worker.copy_to_system_clipboard', return_value=True):
                await worker._run()
            self.assertEqual([job['status'] for job in store.list()], ['skipped','posted'])
            self.assertTrue(any('skipped' in entry['message'] for entry in worker.status()['logs']))
            for i in range(600): worker._set_step(str(i))
            self.assertEqual(len(worker.status()['logs']),500)

    async def test_invalid_timeout_rejected_before_browser_start(self):
        worker = QueueWorker(store=None,browser=None,default_job_delay=0,max_jobs_per_run=1)
        with self.assertRaises(ValueError): worker.start({'composerTimeoutMs':0})

class BrowserFixtureTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.playwright = await async_playwright().start()
        executable = BrowserManager._system_chrome()
        self.browser = await self.playwright.chromium.launch(headless=True, **({'executable_path':executable} if executable else {}))
        self.page = await self.browser.new_page()
    async def asyncTearDown(self):
        await self.browser.close()
        await self.playwright.stop()

    async def test_membership_answers_and_rules_submitted(self):
        await self.page.set_content('''<div role="dialog"><label>Do you agree to the rules?<textarea id="answer"></textarea></label><label><input type="checkbox" id="rules">I agree to group rules</label><button onclick="window.result = [document.querySelector('#answer').value, document.querySelector('#rules').checked]; this.parentElement.remove()">Submit</button></div>''')
        await answer_membership_form(self.page.get_by_role('dialog'), [{'question':'agree','answer':'I agree'}], True, lambda _:None)
        self.assertEqual(await self.page.evaluate('window.result'), ['I agree',True])

    async def test_radio_and_select_answers(self):
        await self.page.set_content('''<div role="dialog"><div role="radiogroup" aria-label="Agree to rules?"><label><input type="radio" name="rules" value="yes">I agree</label><label><input type="radio" name="rules" value="no">No</label></div><label>Location<select><option>Choose</option><option>Sacramento</option></select></label><button onclick="window.result=[document.querySelector('input:checked').value, document.querySelector('select').value]; this.parentElement.remove()">Submit</button></div>''')
        await answer_membership_form(self.page.get_by_role('dialog'), [{'question':'agree','answer':'I agree'}, {'question':'location','answer':'Sacramento'}],False,lambda _:None)
        self.assertEqual(await self.page.evaluate('window.result'), ['yes','Sacramento'])

    async def test_join_immediate_and_existing_membership(self):
        await self.page.set_content("""<button onclick="this.textContent='Joined'">Join Group</button>""")
        await join_group(self.page, lambda _:None, [], True, 1500)
        self.assertTrue(await self.page.get_by_role('button', name='Joined', exact=True).is_visible())
        await self.page.set_content('<button>Write something</button>')
        await join_group(self.page, lambda _:None, [], True, 500)

    async def test_join_form_and_pending_approval(self):
        await self.page.set_content('''<button id="join" onclick="this.hidden=true; document.querySelector('#form').hidden=false">Join Group</button><div id="form" role="dialog" hidden><label>Agree to rules?<textarea></textarea></label><button onclick="this.parentElement.hidden=true; document.querySelector('#pending').hidden=false">Submit</button></div><button id="pending" hidden>Cancel request</button>''')
        with self.assertRaises(AutomationError) as error:
            await join_group(self.page, lambda _:None, [{'question':'agree','answer':'I agree'}], True, 3000)
        self.assertEqual(error.exception.code,'JOIN_PENDING')
        self.assertEqual(await self.page.locator('textarea').input_value(),'I agree')

    async def test_unknown_question_not_submitted(self):
        await self.page.set_content('''<div role="dialog"><label>Where do you live?<textarea></textarea></label><button onclick="window.submitted=true">Submit</button></div>''')
        with self.assertRaises(AutomationError) as error:
            await answer_membership_form(self.page.get_by_role('dialog'), [{'question':'agree','answer':'I agree'}], True, lambda _:None)
        self.assertEqual(error.exception.code,'JOIN_PENDING')
        self.assertIsNone(await self.page.evaluate('window.submitted'))

    async def test_missing_and_unopened_composers_share_deadline(self):
        for html in ['<p>No composer</p>', '<button>Write something</button>']:
            await self.page.set_content(html)
            started = time.monotonic()
            with self.assertRaises(AutomationError) as error:
                await prepare_composer(self.page, lambda _:None, 500)
            self.assertEqual(error.exception.code,'COMPOSER_NOT_FOUND')
            self.assertLess(time.monotonic()-started,1.5)

    async def test_composer_opens_and_returns_editor(self):
        await self.page.set_content('''<button onclick="document.querySelector('#composer').hidden=false">Write something</button><div role="dialog" id="composer" hidden><div contenteditable="true"></div></div>''')
        editor = await prepare_composer(self.page, lambda _:None,1000)
        self.assertTrue(await editor.is_visible())
