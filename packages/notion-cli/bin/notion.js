#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import {
  createNotionClientFromEnv,
  DEFAULT_NOTION_VERSION,
} from "@manfred/notion-core";
import {
  parseArgv,
  parseBoolean,
  parseJsonFromFlagOrFile,
  readJsonFromStdin,
  requireFlag,
} from "../src/args.js";
import { executeOperation, normalizeOperationName } from "../src/operations.js";

function stripWrappingQuotes(value) {
  if (!value) {
    return value;
  }
  if (
    (value.startsWith("\"") && value.endsWith("\"")) ||
    (value.startsWith("'") && value.endsWith("'"))
  ) {
    return value.slice(1, -1);
  }
  return value;
}

function loadDotEnvFile() {
  const envPath = path.join(process.cwd(), ".env");
  if (!fs.existsSync(envPath)) {
    return;
  }

  const lines = fs.readFileSync(envPath, "utf8").split(/\r?\n/u);
  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) {
      continue;
    }

    const withoutExport = line.startsWith("export ")
      ? line.slice("export ".length).trim()
      : line;
    const separatorIdx = withoutExport.indexOf("=");
    if (separatorIdx <= 0) {
      continue;
    }

    const key = withoutExport.slice(0, separatorIdx).trim();
    const value = stripWrappingQuotes(withoutExport.slice(separatorIdx + 1).trim());
    if (!key || process.env[key] !== undefined) {
      continue;
    }
    process.env[key] = value;
  }
}

function printHelp() {
  console.log(`notion - lightweight Notion CLI\n
Environment:
  NOTION_TOKEN (or NOTION_API_KEY)    Notion integration token (auto-loaded from .env)
  NOTION_VERSION                      Optional API version (default: ${DEFAULT_NOTION_VERSION})

Commands:
  notion search --query "text" [--filter-json '{}'] [--sort-json '{}'] [--page-size 20] [--start-cursor CURSOR]
  notion get-page --page-id PAGE_ID
  notion create-page --parent-json '{...}' [--properties-json '{...}'] [--children-json '[...]']
  notion update-page --page-id PAGE_ID [--properties-json '{...}'] [--archived true|false] [--is-locked true|false]
  notion get-data-source --data-source-id DATA_SOURCE_ID
  notion create-data-source --parent-json '{...}' --title-json '[...]' --properties-json '{...}' [--icon-json '{...}'] [--description-json '[...]']
  notion update-data-source --data-source-id DATA_SOURCE_ID [--title-json '[...]'] [--properties-json '{...}'] [--icon-json '{...}'] [--description-json '[...]'] [--archived true|false] [--in-trash true|false]
  notion list-blocks --block-id BLOCK_ID [--page-size 100] [--start-cursor CURSOR] [--all]
  notion append-blocks --block-id BLOCK_ID --children-json '[...]' [--after BLOCK_ID]
  notion update-block --block-id BLOCK_ID --block-json '{...}'
  notion query-data-source --data-source-id DATA_SOURCE_ID [--filter-json '{...}'] [--sorts-json '[...]'] [--page-size 20] [--start-cursor CURSOR]
  notion invoke OPERATION [--input-json '{...}' | --input-file ./payload.json]

Tip:
  Any *-json flag also supports *-file. Example:
  notion append-blocks --block-id ... --children-file ./children.json

Agent mode:
  notion invoke reads JSON from stdin if --input-json/--input-file is not provided.
  OPERATION can be: search, get-page, list-blocks, append-blocks, create-page,
  update-page, get-data-source, create-data-source, update-data-source,
  query-data-source, update-block.
`);
}

async function main() {
  loadDotEnvFile();

  const argv = process.argv.slice(2);
  if (argv.length === 0 || argv.includes("--help") || argv.includes("-h")) {
    printHelp();
    return;
  }

  const command = argv[0];
  const { options } = parseArgv(argv.slice(1));
  const notion = createNotionClientFromEnv();
  let result;

  switch (normalizeOperationName(command)) {
    case "search": {
      result = await executeOperation(notion, "search", {
        query: options.query || "",
        filter: parseJsonFromFlagOrFile(options, "filter-json", "filter-file"),
        sort: parseJsonFromFlagOrFile(options, "sort-json", "sort-file"),
        page_size: options["page-size"] ? Number(options["page-size"]) : undefined,
        start_cursor: options["start-cursor"],
      });
      break;
    }

    case "get-page": {
      result = await executeOperation(notion, "get-page", {
        page_id: requireFlag(options, "page-id"),
      });
      break;
    }

    case "create-page": {
      const parent = parseJsonFromFlagOrFile(options, "parent-json", "parent-file");
      if (!parent) {
        throw new Error("--parent-json or --parent-file is required");
      }

      result = await executeOperation(notion, "create-page", {
        parent,
        properties: parseJsonFromFlagOrFile(
          options,
          "properties-json",
          "properties-file",
        ),
        children: parseJsonFromFlagOrFile(options, "children-json", "children-file"),
      });
      break;
    }

    case "update-page": {
      result = await executeOperation(notion, "update-page", {
        page_id: requireFlag(options, "page-id"),
        properties: parseJsonFromFlagOrFile(
          options,
          "properties-json",
          "properties-file",
        ),
        archived: parseBoolean(options.archived, "archived"),
        is_locked: parseBoolean(options["is-locked"], "is-locked"),
      });
      break;
    }

    case "get-data-source": {
      result = await executeOperation(notion, "get-data-source", {
        data_source_id: requireFlag(options, "data-source-id"),
      });
      break;
    }

    case "create-data-source": {
      const parent = parseJsonFromFlagOrFile(options, "parent-json", "parent-file");
      const title = parseJsonFromFlagOrFile(options, "title-json", "title-file");
      const properties = parseJsonFromFlagOrFile(
        options,
        "properties-json",
        "properties-file",
      );
      if (!parent) {
        throw new Error("--parent-json or --parent-file is required");
      }
      if (!title) {
        throw new Error("--title-json or --title-file is required");
      }
      if (!properties || typeof properties !== "object") {
        throw new Error("--properties-json/--properties-file must be a JSON object");
      }

      result = await executeOperation(notion, "create-data-source", {
        parent,
        title,
        properties,
        icon: parseJsonFromFlagOrFile(options, "icon-json", "icon-file"),
        description: parseJsonFromFlagOrFile(
          options,
          "description-json",
          "description-file",
        ),
      });
      break;
    }

    case "update-data-source": {
      result = await executeOperation(notion, "update-data-source", {
        data_source_id: requireFlag(options, "data-source-id"),
        title: parseJsonFromFlagOrFile(options, "title-json", "title-file"),
        icon: parseJsonFromFlagOrFile(options, "icon-json", "icon-file"),
        description: parseJsonFromFlagOrFile(
          options,
          "description-json",
          "description-file",
        ),
        properties: parseJsonFromFlagOrFile(
          options,
          "properties-json",
          "properties-file",
        ),
        archived: parseBoolean(options.archived, "archived"),
        in_trash: parseBoolean(options["in-trash"], "in-trash"),
      });
      break;
    }

    case "list-blocks": {
      result = await executeOperation(notion, "list-blocks", {
        block_id: requireFlag(options, "block-id"),
        all: options.all === true,
        page_size: options["page-size"] ? Number(options["page-size"]) : undefined,
        start_cursor: options["start-cursor"],
      });
      break;
    }

    case "append-blocks": {
      const children = parseJsonFromFlagOrFile(options, "children-json", "children-file");
      result = await executeOperation(notion, "append-blocks", {
        block_id: requireFlag(options, "block-id"),
        children,
        after: options.after,
      });
      break;
    }

    case "update-block": {
      const payload = parseJsonFromFlagOrFile(options, "block-json", "block-file");
      if (!payload || typeof payload !== "object") {
        throw new Error("--block-json/--block-file must be a JSON object");
      }
      result = await executeOperation(notion, "update-block", {
        block_id: requireFlag(options, "block-id"),
        block: payload,
      });
      break;
    }

    case "query-data-source": {
      result = await executeOperation(notion, "query-data-source", {
        data_source_id: requireFlag(options, "data-source-id"),
        filter: parseJsonFromFlagOrFile(options, "filter-json", "filter-file"),
        sorts: parseJsonFromFlagOrFile(options, "sorts-json", "sorts-file"),
        page_size: options["page-size"] ? Number(options["page-size"]) : undefined,
        start_cursor: options["start-cursor"],
      });
      break;
    }

    case "invoke": {
      const operation = argv[1];
      if (!operation) {
        throw new Error("Missing operation. Usage: notion invoke OPERATION");
      }

      const input =
        parseJsonFromFlagOrFile(options, "input-json", "input-file") ??
        (await readJsonFromStdin());
      result = await executeOperation(notion, operation, input);
      break;
    }

    default:
      throw new Error(`Unknown command: ${command}`);
  }

  console.log(JSON.stringify(result, null, 2));
}

main().catch((error) => {
  console.error(error.message || error);
  process.exit(1);
});
