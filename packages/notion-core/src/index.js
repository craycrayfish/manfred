import { DEFAULT_NOTION_VERSION, NotionClient } from "./notion-client.js";

export { DEFAULT_NOTION_VERSION, NotionClient };

export function createNotionClientFromEnv() {
  const token = process.env.NOTION_TOKEN || process.env.NOTION_API_KEY;
  const version = process.env.NOTION_VERSION || DEFAULT_NOTION_VERSION;
  return new NotionClient({ token, version });
}
