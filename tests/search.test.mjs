import { describe, expect, it } from "vitest";
import { TestDriver } from "testdriverai/vitest/hooks";

// Search flow test for TX BizFinder production (https://www.txbizfinder.com).
// Types a keyword into the main search box, runs the search, and verifies that
// business lead results are rendered. Uses the public data set (no credentials
// or fixtures required — the app is a public read-only search UI).
describe("TX BizFinder — search flow", () => {
  it("searches for a keyword and shows lead results", async (context) => {
    const testdriver = TestDriver(context);

    await testdriver.provision.chrome({ url: "https://www.txbizfinder.com" });

    // Let the Vue SPA hydrate and load initial data.
    await testdriver.wait(8000);

    // Focus the main keyword search field (placeholder: "Search: auto, repair, name...").
    const searchInput = await testdriver.find(
      'the main search text input with placeholder "Search: auto, repair, name..."',
    );
    await searchInput.click();
    await testdriver.type("auto");

    // Run the search.
    const searchButton = await testdriver.find('the "Search leads" button');
    await searchButton.click();

    // Results are paginated (50 per page) and load asynchronously from the API.
    await testdriver.wait(6000);

    const hasResults = await testdriver.assert(
      "a list of Texas business leads / search results is displayed (rows with company details), not an empty state",
    );
    expect(hasResults).toBeTruthy();
  });
});
