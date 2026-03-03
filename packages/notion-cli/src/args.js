import fs from "node:fs";

export function parseArgv(argv) {
  const options = {};
  const positional = [];

  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith("--")) {
      positional.push(token);
      continue;
    }

    const key = token.slice(2);
    const next = argv[i + 1];

    if (next && !next.startsWith("--")) {
      options[key] = next;
      i += 1;
    } else {
      options[key] = true;
    }
  }

  return { options, positional };
}

export function parseJsonInput(raw, flagName) {
  if (raw === undefined || raw === null) {
    return undefined;
  }

  try {
    return JSON.parse(raw);
  } catch (error) {
    throw new Error(`Invalid JSON passed to --${flagName}: ${error.message}`);
  }
}

export function parseJsonFromFlagOrFile(options, jsonKey, fileKey) {
  if (options[fileKey]) {
    const content = fs.readFileSync(options[fileKey], "utf8");
    return parseJsonInput(content, fileKey);
  }

  return parseJsonInput(options[jsonKey], jsonKey);
}

export function requireFlag(options, key) {
  const value = options[key];
  if (value === undefined || value === true || value === "") {
    throw new Error(`Missing required flag --${key}`);
  }
  return value;
}

export function parseBoolean(value, key) {
  if (value === undefined) {
    return undefined;
  }

  if (typeof value === "boolean") {
    return value;
  }

  if (value === "true") {
    return true;
  }
  if (value === "false") {
    return false;
  }

  throw new Error(`Flag --${key} must be true or false`);
}

export async function readJsonFromStdin() {
  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }

  const raw = Buffer.concat(chunks).toString("utf8").trim();
  if (!raw) {
    return {};
  }

  try {
    return JSON.parse(raw);
  } catch (error) {
    throw new Error(`Invalid JSON on stdin: ${error.message}`);
  }
}
