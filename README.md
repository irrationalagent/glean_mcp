# Installation
`git clone https://github.com/irrationalagent/glean_mcp`

`cd glean_mcp`

`python3 -m venv venv`

`source venv/bin/activate`

`pip3 install -e .`

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

# Available Tools

This MCP server provides three main tools for interacting with Mozilla's Glean telemetry system:

## 1. list_apps_tool
Lists all available Glean applications with their identifiers.

**Parameters:** None

**Returns:** JSON array with app metadata including:
- `v1_name`: The v1 identifier for the app (use this with other tools)
- `app_name`: Display name
- `app_id`: Application ID
- `bq_dataset_family`: BigQuery dataset family name
- `canonical_app_name`: Canonical name
- `document_namespace`: Documentation namespace

**Example usage:**
```
> list all glean apps
```

## 2. search_metrics
Search for Glean metrics across all applications using free-text queries.

**Parameters:**
- `query` (required): Search terms (e.g., "startup time", "default browser")
- `app_hint` (optional): App identifier to bias results (e.g., "fenix", "firefox_ios")
- `limit` (optional, default=25): Maximum number of results

**Returns:** JSON array of matching metrics with:
- `id`: Metric identifier
- `name`: Metric name
- `category`: Metric category
- `type`: Metric type (counter, boolean, string, event, etc.)
- `app`: Application name
- `description`: What the metric measures
- `send_in_pings`: Which pings include this metric
- `url`: Link to Glean Dictionary page

**Example usage:**
```
> search for metrics about startup time in fenix
> find metrics tracking default browser on firefox_ios
```

## 3. get_metric_details
Get detailed information about a specific metric including full definition, data reviews, and extra keys.

**Parameters:**
- `v1_name` (required): App identifier (e.g., "fenix", "firefox_ios")
- `metric_name` (required): Full metric name (e.g., "collections.save_button")

**Returns:** JSON object with complete metric details including:
- `latest_definition`: Full metric definition with:
  - `bugs`: Related bug URLs
  - `data_reviews`: Data review links
  - `description`: Detailed description
  - `lifetime`: Metric lifetime (ping, application, etc.)
  - `type`: Metric type
  - `extra_keys`: Event metadata (for event metrics)
  - `data_sensitivity`: Data sensitivity classifications
  - `notification_emails`: Contact emails
  - And more...

**Example usage:**
```
> get details for the metric app.default_browser on firefox_ios
> show me the full definition of collections.save_button on fenix
```

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