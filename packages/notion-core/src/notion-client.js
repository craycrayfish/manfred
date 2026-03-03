const DEFAULT_BASE_URL = "https://api.notion.com/v1";
export const DEFAULT_NOTION_VERSION = "2025-09-03";

function withQuery(path, query) {
  if (!query || Object.keys(query).length === 0) {
    return path;
  }

  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null) {
      continue;
    }
    params.set(key, String(value));
  }

  const queryString = params.toString();
  if (!queryString) {
    return path;
  }

  return `${path}?${queryString}`;
}

function ensureToken(token) {
  if (!token) {
    throw new Error(
      "Missing Notion token. Set NOTION_TOKEN (or NOTION_API_KEY) in your environment.",
    );
  }
}

function normalizeId(id) {
  if (!id) {
    return id;
  }
  return String(id).trim();
}

export class NotionClient {
  constructor({ token, version = DEFAULT_NOTION_VERSION, baseUrl = DEFAULT_BASE_URL, userAgent = "manfred-notion-tools/0.1.0" } = {}) {
    ensureToken(token);
    this.token = token;
    this.version = version;
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.userAgent = userAgent;
  }

  async request(method, path, { body, query } = {}) {
    const url = `${this.baseUrl}${withQuery(path, query)}`;
    const headers = {
      Authorization: `Bearer ${this.token}`,
      "Notion-Version": this.version,
      "Content-Type": "application/json",
      "User-Agent": this.userAgent,
    };

    const response = await fetch(url, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });

    const text = await response.text();
    let payload;
    try {
      payload = text ? JSON.parse(text) : {};
    } catch {
      payload = { raw: text };
    }

    if (!response.ok) {
      const message = payload?.message || payload?.raw || "Unknown Notion API error";
      const code = payload?.code || "unknown_error";
      const error = new Error(`Notion API ${response.status} (${code}): ${message}`);
      error.status = response.status;
      error.code = code;
      error.payload = payload;
      throw error;
    }

    return payload;
  }

  search(params = {}) {
    return this.request("POST", "/search", { body: params });
  }

  getPage(pageId) {
    return this.request("GET", `/pages/${normalizeId(pageId)}`);
  }

  createPage(payload) {
    return this.request("POST", "/pages", { body: payload });
  }

  updatePage(pageId, payload) {
    return this.request("PATCH", `/pages/${normalizeId(pageId)}`, { body: payload });
  }

  createDataSource(payload) {
    return this.request("POST", "/data_sources", { body: payload });
  }

  getBlockChildren(blockId, { start_cursor, page_size } = {}) {
    return this.request("GET", `/blocks/${normalizeId(blockId)}/children`, {
      query: { start_cursor, page_size },
    });
  }

  appendBlockChildren(blockId, { children, after } = {}) {
    return this.request("PATCH", `/blocks/${normalizeId(blockId)}/children`, {
      body: { children, after },
    });
  }

  updateBlock(blockId, payload) {
    return this.request("PATCH", `/blocks/${normalizeId(blockId)}`, { body: payload });
  }

  queryDataSource(dataSourceId, payload = {}) {
    return this.request("POST", `/data_sources/${normalizeId(dataSourceId)}/query`, {
      body: payload,
    });
  }

  getDataSource(dataSourceId) {
    return this.request("GET", `/data_sources/${normalizeId(dataSourceId)}`);
  }

  updateDataSource(dataSourceId, payload) {
    return this.request("PATCH", `/data_sources/${normalizeId(dataSourceId)}`, {
      body: payload,
    });
  }

  async listAllBlockChildren(blockId, { page_size = 100 } = {}) {
    const all = [];
    let start_cursor;

    do {
      const page = await this.getBlockChildren(blockId, { start_cursor, page_size });
      all.push(...(page.results || []));
      start_cursor = page.has_more ? page.next_cursor : undefined;
    } while (start_cursor);

    return all;
  }
}
