# Config
At the moment, only a single config command is implemented

## Create
Creates a new configuration file in `~/.config/xsoar-cli/config.json` based on a template. If the file already exists, then the user is prompted to overwrite
the existing file.

## Get
Reads the current configuration file and prints it out as JSON indented with 4 whitespaces. API keys are masked from output.

## Validate
Ensures that the configuration file is valid parsable JSON and that each server environment defined is reachable.
