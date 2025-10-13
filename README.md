# Installation
`git clone https://github.com/irrationalagent/glean_mcp`

`cd glean_mcp`

`python3 -m venv venv`

`source venv/bin/activate`

`pip install -e .`

# Run (Standalone)
`glean-mcp`

# Configure for Use w/ Claude CLI
Add the following to `.mcp.json`, making sure to specify the right path:

```json
    "mcpServers": {
      "glean": {
        "command": "/some/path/glean_mcp/venv/bin/glean-mcp",
        "args": []
      }
    }
```
start claude:
`claude`

List MCP servers:
`/mcp`

# Example
`> please find the probe on firefox_ios that tracks whether the browser is set to default`

```
⏺ I'll search for Firefox iOS probes related to default browser status.

⏺ glean - search_metrics (MCP)(query: "default browser", app_hint: "firefox_ios", limit: 25)
  ⎿  [                                                                                                                           
       {
         "id": "default_browser_card.dismiss_pressed",
[...]

⏺ I found the probe that tracks whether Firefox iOS is set as the default browser:

  app.default_browser
  - Type: boolean
  - Description: Is Firefox the default browser

  Additionally, there are related probes that provide context:

  app.opened_as_default_browser
  - Type: counter
  - Description: Counts the number of times the app is opened from an external link, implying the client has Firefox set as a
  default browser. Currently this is the most accurate way of measuring how often Firefox is set as the default browser.

  app.last_opened_as_default_browser
  - Type: datetime
  - Description: The date of when the app was last opened as default browser.

  The app.default_browser boolean probe is the direct indicator, while app.opened_as_default_browser is noted as being the most
  accurate measurement method since it tracks actual usage as the default browser rather than just the setting state.
  ```