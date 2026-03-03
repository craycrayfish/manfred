function required(input, key) {
  if (input[key] === undefined || input[key] === null || input[key] === "") {
    throw new Error(`Missing required field: ${key}`);
  }
  return input[key];
}

export function normalizeOperationName(name) {
  return String(name || "")
    .trim()
    .toLowerCase()
    .replaceAll("_", "-");
}

export async function executeOperation(notion, operationName, input = {}) {
  const operation = normalizeOperationName(operationName);

  switch (operation) {
    case "search":
      return notion.search({
        query: input.query || "",
        filter: input.filter,
        sort: input.sort,
        page_size: input.page_size,
        start_cursor: input.start_cursor,
      });

    case "get-page":
      return notion.getPage(required(input, "page_id"));

    case "create-page":
      return notion.createPage({
        parent: required(input, "parent"),
        properties: input.properties,
        children: input.children,
      });

    case "create-data-source":
      return notion.createDataSource({
        parent: required(input, "parent"),
        title: required(input, "title"),
        properties: required(input, "properties"),
        icon: input.icon,
        description: input.description,
      });

    case "update-page":
      return notion.updatePage(required(input, "page_id"), {
        properties: input.properties,
        archived: input.archived,
        is_locked: input.is_locked,
      });

    case "list-blocks": {
      const blockId = required(input, "block_id");
      if (input.all === true) {
        const rows = await notion.listAllBlockChildren(blockId, {
          page_size: input.page_size,
        });
        return { object: "list", results: rows, has_more: false, next_cursor: null };
      }

      return notion.getBlockChildren(blockId, {
        page_size: input.page_size,
        start_cursor: input.start_cursor,
      });
    }

    case "append-blocks":
      if (!Array.isArray(input.children) || input.children.length === 0) {
        throw new Error("Field children must be a non-empty array");
      }
      return notion.appendBlockChildren(required(input, "block_id"), {
        children: input.children,
        after: input.after,
      });

    case "update-block":
      return notion.updateBlock(required(input, "block_id"), required(input, "block"));

    case "query-data-source":
      return notion.queryDataSource(required(input, "data_source_id"), {
        filter: input.filter,
        sorts: input.sorts,
        page_size: input.page_size,
        start_cursor: input.start_cursor,
      });

    case "get-data-source":
      return notion.getDataSource(required(input, "data_source_id"));

    case "update-data-source":
      return notion.updateDataSource(required(input, "data_source_id"), {
        title: input.title,
        icon: input.icon,
        description: input.description,
        properties: input.properties,
        archived: input.archived,
        in_trash: input.in_trash,
      });

    default:
      throw new Error(`Unknown operation: ${operationName}`);
  }
}
