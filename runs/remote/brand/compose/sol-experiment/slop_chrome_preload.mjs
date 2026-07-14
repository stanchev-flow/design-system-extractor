// Lane-local runtime adapter: the shared audit stays untouched while Playwright uses
// the supervised workstation's installed Chrome after its cached browser disappeared.
import { chromium } from "playwright";

const launch = chromium.launch.bind(chromium);
chromium.launch = (options = {}) =>
  launch({
    ...options,
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  });
