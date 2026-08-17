import { rm } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const outputDirectory = resolve(projectRoot, "html");

if (dirname(outputDirectory) !== projectRoot || outputDirectory === projectRoot) {
    throw new Error(`Refusing to remove unsafe output path: ${outputDirectory}`);
}

await rm(outputDirectory, { recursive: true, force: true });
