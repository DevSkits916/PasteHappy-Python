# Facebook Groups Exporter

## Install locally

1. Open `chrome://extensions` in Chrome.
2. Turn on **Developer mode**.
3. Choose **Load unpacked**.
4. Select this folder.
5. Open a Facebook Groups page. The exporter panel appears in the lower-right corner.

The extension runs only on `facebook.com` and `m.facebook.com` pages whose URL contains `groups`. Collected results remain in the browser's site storage when **Persist results** is enabled.

## Notes

- This is an unpacked extension, intended for local use. Chrome does not allow direct installation of a ZIP file; extract the ZIP before selecting it with **Load unpacked**.
- Facebook can change its page structure at any time, which may require updating the page parsing selectors.
