#!/usr/bin/env node

// src/index.ts
import { existsSync, promises as fs2 } from "fs";
import path2 from "path";
import { Command } from "commander";
import { execa } from "execa";
import ora from "ora";
import prompts from "prompts";

// src/utils/get-components.ts
import fetch from "node-fetch";
import * as z from "zod";
var baseUrl = process.env.COMPONENTS_BASE_URL ?? "https://ui.shadcn.com";
var componentSchema = z.object({
  name: z.string(),
  dependencies: z.array(z.string()).optional(),
  files: z.array(
    z.object({
      name: z.string(),
      dir: z.string(),
      content: z.string()
    })
  )
});
var componentsSchema = z.array(componentSchema);
async function getAvailableComponents() {
  try {
    const response = await fetch(`${baseUrl}/api/components`);
    const components = await response.json();
    return componentsSchema.parse(components);
  } catch (error) {
    throw new Error(
      `Failed to fetch components from ${baseUrl}/api/components.`
    );
  }
}

// src/utils/get-package-info.ts
import path from "path";
import fs from "fs-extra";
function getPackageInfo() {
  const packageJsonPath = path.join("package.json");
  return fs.readJSONSync(packageJsonPath);
}

// src/utils/get-package-manager.ts
function getPackageManager() {
  const userAgent = process.env.npm_config_user_agent;
  if (!userAgent) {
    return "npm";
  }
  if (userAgent.startsWith("yarn")) {
    return "yarn";
  }
  if (userAgent.startsWith("pnpm")) {
    return "pnpm";
  }
  return "npm";
}

// src/utils/logger.ts
import chalk from "chalk";
var logger = {
  error(...args) {
    console.log(chalk.red(...args));
  },
  warn(...args) {
    console.log(chalk.yellow(...args));
  },
  info(...args) {
    console.log(chalk.cyan(...args));
  },
  success(...args) {
    console.log(chalk.green(...args));
  }
};

// src/index.ts
process.on("SIGINT", () => process.exit(0));
process.on("SIGTERM", () => process.exit(0));
async function main() {
  const packageInfo = await getPackageInfo();
  const program = new Command().name("@shadcn/ui").description("Add @shadcn/ui components to your project").version(
    packageInfo.version || "1.0.0",
    "-v, --version",
    "display the version number"
  );
  program.command("add").description("add components to your project").action(async () => {
    logger.warn(
      "Running the following command will overwrite existing files."
    );
    logger.warn(
      "Make sure you have committed your changes before proceeding."
    );
    logger.warn("");
    const { components, dir } = await promptForAddOptions();
    if (!components?.length) {
      logger.warn("No components selected. Nothing to install.");
      process.exit(0);
    }
    const destinationDir = path2.resolve(dir);
    if (!existsSync(destinationDir)) {
      const spinner = ora(`Creating ${dir}...`).start();
      await fs2.mkdir(destinationDir, { recursive: true });
      spinner.succeed();
    }
    const packageManager = getPackageManager();
    logger.success(`Installing components...`);
    for (const component of components) {
      const componentSpinner = ora(`${component.name}...`).start();
      for (const file of component.files) {
        const filePath = path2.resolve(dir, file.name);
        await fs2.writeFile(filePath, file.content);
      }
      if (component.dependencies?.length) {
        const dependencies = component.dependencies.join(" ");
        await execa(packageManager, [
          packageManager === "npm" ? "install" : "add",
          dependencies
        ]);
      }
      componentSpinner.succeed(component.name);
    }
  });
  program.parse();
}
async function promptForAddOptions() {
  const availableComponents = await getAvailableComponents();
  if (!availableComponents?.length) {
    logger.error(
      "An error occurred while fetching components. Please try again."
    );
    process.exit(0);
  }
  const options = await prompts([
    {
      type: "multiselect",
      name: "components",
      message: "Which component(s) would you like to add?",
      hint: "Space to select. A to select all. I to invert selection.",
      instructions: false,
      choices: availableComponents.map((component) => ({
        title: component.name,
        value: component
      }))
    },
    {
      type: "text",
      name: "dir",
      message: "Where would you like to install the component(s)?",
      initial: "./components/ui"
    }
  ]);
  return options;
}
main();
//# sourceMappingURL=index.js.map