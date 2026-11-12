# Azure DevOps Terraform Plan Task

## Overview

This pipeline section runs `terraform plan` through the Azure DevOps
`AzureCLI@2` task. It:

1.  Authenticates to Azure through an Azure DevOps Service Connection.
2.  Exposes the Service Principal details to the Bash script.
3.  Configures Terraform's Azure authentication using OIDC when
    available, otherwise a client secret.
4.  Builds optional Terraform plan arguments (destroy mode, resource
    targets, and additional arguments).
5.  Generates and saves a binary Terraform plan.
6.  Copies the Terraform lock file and an optional additional artifact
    into the artifact staging directory.
7.  Displays the saved plan in the pipeline logs.

The task prepares a plan for review and a later apply stage. It does
**not** apply infrastructure changes.

## 1. AzureCLI@2 task configuration

``` yaml
- task: AzureCLI@2
  displayName: Terraform Plan
  inputs:
    azureSubscription: '${{ parameters.azureServiceConnection }}'
    scriptType: bash
    scriptLocation: inlineScript
    workingDirectory: '${{ parameters.workingDirectory }}'
    addSpnToEnvironment: true
```

  -----------------------------------------------------------------------
  Setting                             Purpose
  ----------------------------------- -----------------------------------
  `AzureCLI@2`                        Runs Azure CLI commands in an Azure
                                      DevOps pipeline.

  `azureSubscription`                 Selects the Azure Resource Manager
                                      Service Connection used to
                                      authenticate to Azure.

  `scriptType: bash`                  Runs the inline script using Bash.

  `scriptLocation: inlineScript`      Indicates that the script is
                                      defined in the YAML.

  `workingDirectory`                  Sets the directory from which the
                                      script runs.

  `addSpnToEnvironment: true`         Makes Service Connection identity
                                      values available to the script as
                                      environment variables.
  -----------------------------------------------------------------------

With `addSpnToEnvironment: true`, the task exposes values such as:

-   `servicePrincipalId`: the Service Principal/application client ID.
-   `tenantId`: the Microsoft Entra tenant ID.
-   `servicePrincipalKey`: the client secret when secret-based
    authentication is used.
-   `idToken`: a federated token when the Service Connection uses
    workload identity federation (OIDC).

The exact authentication values available depend on the Service
Connection configuration.

## 2. Bash safety options

``` bash
set -euo pipefail
```

This enables three Bash options:

  -----------------------------------------------------------------------
  Option                              Meaning
  ----------------------------------- -----------------------------------
  `-e`                                Exit when a command fails (subject
                                      to Bash's normal exceptions for
                                      conditionals and compound
                                      commands).

  `-u`                                Treat references to unset variables
                                      as errors.

  `-o pipefail`                       Make a pipeline return a failure if
                                      any command in it fails, rather
                                      than only considering the final
                                      command.
  -----------------------------------------------------------------------

These options help prevent the script from silently continuing after
errors.

## 3. Configure Terraform Azure authentication

``` bash
export ARM_CLIENT_ID="${servicePrincipalId}"
export ARM_TENANT_ID="${tenantId}"
export ARM_SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
```

The AzureRM Terraform provider can read these `ARM_` environment
variables to identify the Azure application, tenant, and subscription.

  Variable                Purpose
  ----------------------- ------------------------------------------
  `ARM_CLIENT_ID`         Service Principal/application client ID.
  `ARM_TENANT_ID`         Microsoft Entra tenant ID.
  `ARM_SUBSCRIPTION_ID`   Azure subscription ID.

### Understanding the subscription command

``` bash
az account show --query id -o tsv
```

-   `az account show` retrieves details about the currently active Azure
    CLI account.
-   `--query id` extracts the subscription ID using JMESPath.
-   `-o tsv` outputs the value as plain text.

The script exports the result as `ARM_SUBSCRIPTION_ID`, making it
available to Terraform and its child processes.

### OIDC or client-secret authentication

``` bash
if [ -n "${idToken:-}" ]; then
  export ARM_USE_OIDC=true
  export ARM_OIDC_TOKEN="${idToken}"
else
  export ARM_CLIENT_SECRET="${servicePrincipalKey}"
fi
```

The script supports two authentication paths.

#### Option A: OIDC / workload identity federation

When `idToken` is non-empty:

1.  Azure DevOps obtains a federated identity token through the
    configured Service Connection.
2.  The script enables OIDC authentication for Terraform.
3.  The token is passed to Terraform through `ARM_OIDC_TOKEN`.
4.  Terraform uses the federated identity to authenticate to Azure.

``` bash
export ARM_USE_OIDC=true
export ARM_OIDC_TOKEN="${idToken}"
```

OIDC avoids storing and rotating a long-lived client secret in the
pipeline.

#### Option B: Service Principal client secret

When no `idToken` is available, the script falls back to:

``` bash
export ARM_CLIENT_SECRET="${servicePrincipalKey}"
```

Terraform then authenticates using the Service Principal client ID,
tenant ID, subscription ID, and client secret.

> **Important:** `addSpnToEnvironment: true` exposes the identity values
> to the script. It does not, by itself, configure OIDC. The Azure
> DevOps Service Connection must be configured for workload identity
> federation for the OIDC path to work.

### Why use `${idToken:-}`?

The script starts with `set -u`, which makes an unset variable an error.
The Bash expression `${idToken:-}` safely expands to an empty string if
`idToken` is unset.

The `-n` test checks whether the resulting string is non-empty.

## 4. Select the plan mode

``` bash
plan_mode=()

if [ '${{ parameters.action }}' = 'destroy' ]; then
  plan_mode=(-destroy)
fi
```

This creates an array of optional Terraform arguments.

-   For a normal plan, `plan_mode` remains empty.
-   When `parameters.action` is `destroy`, the array contains
    `-destroy`.

The array is later expanded using:

``` bash
"${plan_mode[@]}"
```

This is useful because an empty array contributes no arguments, while a
populated array contributes its individual arguments.

Examples:

  `parameters.action`   Effective plan mode
  --------------------- ---------------------------
  `plan`                Normal plan
  `destroy`             `terraform plan -destroy`

A destroy plan previews resource destruction; it does not destroy
resources until a corresponding apply operation is performed.

## 5. Build resource target arguments

``` bash
target_args=()

while IFS= read -r target; do
  if [ -n "${target}" ]; then
    target_args+=("-target=${target}")
  fi
done < <(printf '%s' "${TERRAFORM_TARGETS_JSON}" | jq -r '.[]')
```

This section converts a JSON array of Terraform resource addresses into
Bash arguments.

The environment variable is populated in the task's `env` block:

``` yaml
TERRAFORM_TARGETS_JSON: ${{ convertToJson(parameters.terraformTargets) }}
```

For example, the template parameter could be:

``` yaml
terraformTargets:
  - azurerm_resource_group.main
  - azurerm_virtual_network.main
```

`convertToJson` turns the parameter into:

``` json
[
  "azurerm_resource_group.main",
  "azurerm_virtual_network.main"
]
```

The command:

``` bash
printf '%s' "${TERRAFORM_TARGETS_JSON}" | jq -r '.[]'
```

uses `jq` to print each JSON array element on its own line.

The `while` loop reads each line and adds a `-target=` argument to the
array. The resulting array is equivalent to:

``` bash
target_args=(
  "-target=azurerm_resource_group.main"
  "-target=azurerm_virtual_network.main"
)
```

Terraform receives these as separate command-line arguments.

> **Caution:** Terraform recommends using `-target` only in exceptional
> situations, such as recovery or working around limitations. It can
> produce a partial view of the configuration and should not normally
> replace a full plan.

## 6. Build additional plan arguments

``` bash
additional_plan_args=()

while IFS= read -r argument; do
  if [ -n "${argument}" ]; then
    additional_plan_args+=("${argument}")
  fi
done < <(printf '%s' "${ADDITIONAL_PLAN_ARGUMENTS_JSON}" | jq -r '.[]')
```

This follows the same pattern as the target handling, but it accepts
general Terraform plan arguments.

The JSON value is supplied by:

``` yaml
ADDITIONAL_PLAN_ARGUMENTS_JSON: ${{ convertToJson(parameters.additionalPlanArguments) }}
```

For example:

``` yaml
additionalPlanArguments:
  - "-refresh=true"
  - "-replace=azurerm_virtual_machine.example"
```

The script converts this into:

``` bash
additional_plan_args=(
  "-refresh=true"
  "-replace=azurerm_virtual_machine.example"
)
```

This makes the template more reusable: callers can pass supported
Terraform plan options without changing the shared script.

Only pass arguments that are valid for `terraform plan`, and validate
any user-controlled values before passing them to the command.

## 7. Run Terraform plan and save the result

``` bash
terraform plan -input=false -lock-timeout=5m \
  "${plan_mode[@]}" \
  "${target_args[@]}" \
  "${additional_plan_args[@]}" \
  -var-file="${{ parameters.tfvarsFile }}" \
  -out="$(Build.ArtifactStagingDirectory)/${{ parameters.planFileName }}"
```

  -----------------------------------------------------------------------
  Argument                            Purpose
  ----------------------------------- -----------------------------------
  `terraform plan`                    Creates an execution plan showing
                                      proposed infrastructure changes.

  `-input=false`                      Disables interactive input prompts,
                                      which are unsuitable for unattended
                                      pipeline runs.

  `-lock-timeout=5m`                  Waits up to five minutes to acquire
                                      the state lock before failing.

  `"${plan_mode[@]}"`                 Adds `-destroy` when destroy mode
                                      is selected.

  `"${target_args[@]}"`               Adds any requested resource
                                      targets.

  `"${additional_plan_args[@]}"`      Adds any extra plan arguments.

  `-var-file=...`                     Loads input variable values from
                                      the specified `.tfvars` file.

  `-out=...`                          Saves the generated plan to a
                                      binary plan file.
  -----------------------------------------------------------------------

### Why save the plan with `-out`?

The `-out` option saves the plan instead of only printing it to the
terminal.

For example, if:

``` yaml
planFileName: terraform.tfplan
```

Terraform writes the plan to:

``` text
$(Build.ArtifactStagingDirectory)/terraform.tfplan
```

A later deployment stage can download this file and apply the saved
plan:

``` bash
terraform apply -input=false terraform.tfplan
```

This allows the pipeline to separate planning and review from
deployment. The apply stage uses the saved plan rather than creating a
new plan at apply time.

A saved plan is a binary artifact and may contain sensitive information,
including values that are not displayed in normal terminal output.
Protect it with appropriate pipeline artifact permissions and retention
policies.

## 8. Copy the Terraform dependency lock file

``` bash
cp .terraform.lock.hcl \
  "$(Build.ArtifactStagingDirectory)/.terraform.lock.hcl"
```

The `.terraform.lock.hcl` file records the selected provider versions
and their checksums.

Copying it alongside the plan helps the later stage use the same locked
provider selections.

The lock file should also be committed to source control. Copying it
into the artifact does not replace that practice.

## 9. Copy an optional additional artifact

``` bash
additional_artifact='${{ parameters.additionalArtifactFile }}'

if [ -n "${additional_artifact}" ] && [ -f "${additional_artifact}" ]; then
  relative_path="${additional_artifact#$(Build.SourcesDirectory)/}"
  artifact_path="$(Build.ArtifactStagingDirectory)/${relative_path}"
  mkdir -p "$(dirname "${artifact_path}")"
  cp "${additional_artifact}" "${artifact_path}"
fi
```

This section optionally copies another file into the artifact staging
directory.

For example:

``` yaml
additionalArtifactFile: '$(Build.SourcesDirectory)/config/deployment.json'
```

The script performs these operations:

1.  Checks that the parameter is non-empty (`-n`) and points to an
    existing regular file (`-f`).
2.  Removes the `$(Build.SourcesDirectory)/` prefix to calculate a
    relative path.
3.  Builds the destination path under
    `$(Build.ArtifactStagingDirectory)`.
4.  Creates the destination's parent directory using `mkdir -p`.
5.  Copies the file to the destination using `cp`.

For example:

``` text
Source:
$(Build.SourcesDirectory)/config/deployment.json

Relative path:
config/deployment.json

Destination:
$(Build.ArtifactStagingDirectory)/config/deployment.json
```

If the parameter is empty or the file does not exist, this optional copy
is skipped.

## 10. Environment variables passed to the task

``` yaml
env:
  TF_IN_AUTOMATION: $(TF_IN_AUTOMATION)
  TF_INPUT: $(TF_INPUT)
  TF_PLUGIN_CACHE_DIR: $(TF_PLUGIN_CACHE_DIR)
  TERRAFORM_TARGETS_JSON: ${{ convertToJson(parameters.terraformTargets) }}
  ADDITIONAL_PLAN_ARGUMENTS_JSON: ${{ convertToJson(parameters.additionalPlanArguments) }}
```

The `env` block injects variables into the task's process environment.

  -----------------------------------------------------------------------
  Variable                            Purpose
  ----------------------------------- -----------------------------------
  `TF_IN_AUTOMATION`                  Tells Terraform it is running in an
                                      automation environment, allowing it
                                      to adjust some output behavior.

  `TF_INPUT`                          Controls whether Terraform prompts
                                      for input.

  `TF_PLUGIN_CACHE_DIR`               Specifies the directory used to
                                      cache downloaded Terraform provider
                                      plugins.

  `TERRAFORM_TARGETS_JSON`            Carries the resource target list as
                                      JSON.

  `ADDITIONAL_PLAN_ARGUMENTS_JSON`    Carries extra plan arguments as
                                      JSON.
  -----------------------------------------------------------------------

### Azure DevOps expression syntax

Two different Azure DevOps syntaxes appear here:

-   `${{ ... }}`: compile-time template expressions. These are evaluated
    while Azure DevOps expands the YAML template.
-   `$(...)`: runtime variable macros. These are expanded when the
    pipeline task runs.

For example:

``` yaml
${{ convertToJson(parameters.terraformTargets) }}
```

converts a template parameter into JSON, whereas:

``` yaml
$(TF_PLUGIN_CACHE_DIR)
```

references an Azure DevOps pipeline variable.

## 11. Display the saved plan

After the Azure CLI task, a separate Bash task runs:

``` yaml
- bash: |
    set -euo pipefail
    terraform show -no-color \
      "$(Build.ArtifactStagingDirectory)/${{ parameters.planFileName }}"
  displayName: Show Planned Terraform Changes
  workingDirectory: '${{ parameters.workingDirectory }}'
```

`terraform show` reads and displays the saved plan.

-   `terraform show`: displays a Terraform plan or state.
-   `-no-color`: removes ANSI color codes, making the output easier to
    read in pipeline logs.
-   The final argument: points to the binary plan generated by the
    previous task.

Example output:

``` text
# azurerm_resource_group.example will be created

+ resource "azurerm_resource_group" "example" {
    + location = "Germany West Central"
    + name     = "rg-example"
  }

Plan: 1 to add, 0 to change, 0 to destroy.
```

This provides visibility into the planned changes in the pipeline logs.
It does not approve or apply them.

## 12. End-to-end execution flow

``` text
Azure DevOps Pipeline
        |
        v
AzureCLI@2 authenticates using the Service Connection
        |
        v
Service Principal details are exposed to the Bash script
        |
        v
Configure Terraform ARM_* authentication variables
        |
        +---- idToken available? ----+
        |                            |
       Yes                           No
        |                            |
        v                            v
 Configure OIDC              Configure client secret
        |                            |
        +-------------+--------------+
                      |
                      v
       Build optional Terraform arguments
       - destroy mode
       - resource targets
       - additional plan arguments
                      |
                      v
              terraform plan
                      |
                      v
        Save binary plan using -out
                      |
                      v
       Copy .terraform.lock.hcl and any
             optional extra artifact
                      |
                      v
             terraform show
                      |
                      v
          Ready for review and apply
```

## 13. Important implementation considerations

1.  **Terraform initialization:** This task assumes `terraform init` has
    already completed successfully in the configured working directory.
    The backend and providers must be initialized before running the
    plan.

2.  **Terraform and provider consistency:** The apply stage should use a
    compatible Terraform CLI version and the same provider selections
    used to generate the plan.

3.  **OIDC configuration:** The Service Connection must be configured
    for workload identity federation. Merely setting
    `addSpnToEnvironment: true` does not enable OIDC.

4.  **Plan artifact security:** A saved plan can contain sensitive data.
    Restrict artifact access and configure an appropriate retention
    period.

5.  **Plan review and approval:** `terraform show` only displays the
    planned changes. It does not implement an approval gate. Configure a
    separate approval mechanism if deployment approval is required.

6.  **Artifact publishing:** Copying files into
    `$(Build.ArtifactStagingDirectory)` does not publish them
    automatically. Add a `PublishPipelineArtifact@1` task (or an
    equivalent publishing task) to make them available to another job or
    stage.

7.  **State and plan validity:** Terraform plans are tied to the
    configuration and state context used to create them. If the state or
    relevant inputs change before apply, the saved plan may no longer be
    applicable.

8.  **JSON tooling:** The script requires `jq` to be installed and
    available on the agent.

9.  **Shell and path handling:** The optional artifact path logic
    assumes the supplied path is under `$(Build.SourcesDirectory)`.
    Validate the parameter and paths if callers can supply arbitrary
    values.

## 14. Key takeaway

This task implements the **Terraform planning part** of a CI/CD
workflow:

-   `terraform plan` calculates the proposed infrastructure changes.
-   `-out` saves the exact plan for a later stage.
-   `terraform show` makes the plan readable in pipeline logs.
-   The lock file and optional supporting files are staged alongside the
    plan.
-   A separate apply stage can download the published artifact and run
    `terraform apply` against the saved plan.

The separation between plan, review/approval, and apply creates a more
controlled and auditable infrastructure deployment process.
