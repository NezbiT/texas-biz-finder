import { describe, expect, it } from "vitest";
import { TestDriver } from "testdriverai/vitest/hooks";

// Smoke test for TX BizFinder production (https://www.txbizfinder.com).
// TX BizFinder is a public Texas small-business search app (no login required),
// so this exercises the core public surface: the app loads and renders its
// search + filter controls and the "Texas businesses" stats header.
describe("TX BizFinder — smoke", () => {
  it("loads the production app and shows the search interface", async (context) => {
    const testdriver = TestDriver(context);

    await testdriver.provision.chrome({ url: "https://www.txbizfinder.com" });

    // The frontend is a Vue SPA that fetches stats after load — give it time.
    await testdriver.wait(8000);

    const appVisible = await testdriver.assert(
      "the TX BizFinder Texas business search application is visible with search and filter controls",
    );
    expect(appVisible).toBeTruthy();

    const statsVisible = await testdriver.assert(
      "a 'Texas businesses' statistic with a large count is shown in the header",
    );
    expect(statsVisible).toBeTruthy();

    const searchButtonVisible = await testdriver.assert(
      "a 'Search leads' button and an 'Export CSV' button are visible",
    );
    expect(searchButtonVisible).toBeTruthy();
  });
});
