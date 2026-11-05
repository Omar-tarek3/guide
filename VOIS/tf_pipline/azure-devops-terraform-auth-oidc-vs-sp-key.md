# Azure DevOps Service Connection Authentication for Terraform

## 1. Overview

When a pipeline needs to deploy or manage Azure resources, Terraform
must authenticate to Azure.

A common approach is to use an Azure DevOps **Azure Resource Manager
(ARM) service connection** with the `AzureCLI@2` task.

The service connection handles the pipeline's Azure sign-in. The task
can also expose the service connection's authentication details to the
script, so Terraform can use them.

``` yaml
- task: AzureCLI@2
  displayName: Authenticate and run Terraform
  inputs:
    azureSubscription: 'my-azure-service-connection'
    scriptType: bash
    scriptLocation: inlineScript
    addSpnToEnvironment: true
    inlineScript: |
      # Terraform commands go here
      terraform init
      terraform plan
```

### What does `addSpnToEnvironment: true` do?

It asks `AzureCLI@2` to make the service connection's service-principal
authentication information available to the inline script as environment
variables.

It does **not** create a service connection, grant Azure permissions, or
perform a second login. The Azure CLI task authenticates using the
selected service connection.

For service-principal authentication, the task exposes values such as:

  -----------------------------------------------------------------------
  Variable                            Meaning
  ----------------------------------- -----------------------------------
  `servicePrincipalId`                Application/client ID

  `tenantId`                          Microsoft Entra tenant ID

  `servicePrincipalKey`               Client secret, when the connection
                                      uses a secret

  `idToken`                           Federated ID token, when workload
                                      identity federation is used
  -----------------------------------------------------------------------

The values available depend on the service connection's authentication
method. Do not print secrets or tokens in pipeline logs.

------------------------------------------------------------------------

## 2. Service principal secret authentication (SP key)

With secret-based authentication, the service principal has a **client
secret**. The pipeline uses the client ID, tenant ID, and secret to
authenticate.

### Authentication flow

1.  Azure DevOps starts the pipeline.
2.  `AzureCLI@2` uses the configured ARM service connection.
3.  The service connection authenticates using its client ID and client
    secret.
4.  With `addSpnToEnvironment: true`, the task exposes the relevant
    values to the script.
5.  Terraform uses those credentials to authenticate to Azure.

### Example

``` yaml
- task: AzureCLI@2
  displayName: Terraform deployment (client secret)
  inputs:
    azureSubscription: 'my-sp-secret-service-connection'
    scriptType: bash
    scriptLocation: inlineScript
    addSpnToEnvironment: true
    inlineScript: |
      export ARM_CLIENT_ID="$servicePrincipalId"
      export ARM_TENANT_ID="$tenantId"
      export ARM_CLIENT_SECRET="$servicePrincipalKey"
      export ARM_SUBSCRIPTION_ID="$(az account show --query id -o tsv)"

      terraform init
      terraform plan
```

**Important:** This example is for a service connection that uses a
client secret. Do not use `ARM_CLIENT_SECRET` for a workload identity
federation connection.

### Considerations

-   A client secret is a long-lived credential until it expires or is
    rotated/revoked.
-   The secret must be stored and protected by the service connection;
    never hardcode it in YAML or source control.
-   Secret expiration requires rotation and updating the service
    connection.
-   Anyone who obtains the secret may be able to authenticate as that
    service principal, subject to its permissions.

------------------------------------------------------------------------

## 3. OpenID Connect (OIDC) / Workload identity federation

With workload identity federation, Azure DevOps does not need to store a
client secret for the service connection.

Instead, Azure DevOps obtains a short-lived **OIDC ID token**. Microsoft
Entra ID validates the token's issuer, subject, and audience against a
federated identity credential configured on the application or managed
identity. If the claims match, Entra ID issues an Azure access token for
the requested resource.

### Authentication flow

1.  Azure DevOps starts the pipeline.
2.  The Azure DevOps service connection requests a short-lived OIDC ID
    token.
3.  The pipeline presents that token to Microsoft Entra ID.
4.  Entra ID validates the configured federated identity credential
    (issuer, subject, and audience).
5.  Entra ID issues an access token.
6.  Terraform uses the federated identity flow to authenticate to Azure.

### Example

The following illustrates the environment configuration for Terraform's
AzureRM provider using OIDC. It assumes the Azure DevOps service
connection is configured for workload identity federation and that the
task exposes `idToken`.

``` yaml
- task: AzureCLI@2
  displayName: Terraform deployment (OIDC)
  inputs:
    azureSubscription: 'my-oidc-service-connection'
    scriptType: bash
    scriptLocation: inlineScript
    addSpnToEnvironment: true
    inlineScript: |
      export ARM_CLIENT_ID="$servicePrincipalId"
      export ARM_TENANT_ID="$tenantId"
      export ARM_SUBSCRIPTION_ID="$(az account show --query id -o tsv)"

      export ARM_USE_OIDC=true
      export ARM_OIDC_TOKEN="$idToken"

      terraform init
      terraform plan
```

The exact OIDC environment-variable requirements can depend on the
Terraform AzureRM provider version and authentication configuration.
Check the provider documentation for the version pinned by your project.

**Do not set `ARM_CLIENT_SECRET` in the OIDC flow.** OIDC is intended to
avoid a stored client secret.

------------------------------------------------------------------------

## 4. OIDC vs. SP key (client secret)

  -----------------------------------------------------------------------
  Area                    OIDC / workload         SP key / client secret
                          identity federation     
  ----------------------- ----------------------- -----------------------
  Credential              Short-lived federated   Client secret
                          ID token exchanged with 
                          Entra ID                

  Stored secret           No client secret needs  Secret is stored in the
                          to be stored in the     service connection
                          service connection      

  Lifetime                ID token is short-lived Secret can remain valid
                                                  for months, depending
                                                  on its configured
                                                  expiry

  Rotation                No client-secret        Secret must be rotated
                          rotation                before expiry

  Trust model             Entra ID trusts a       Entra ID validates the
                          configured issuer,      client ID and secret
                          subject, and audience   

  Pipeline setup          Requires a correctly    Requires a valid client
                          configured federated    secret
                          identity credential     

  Security posture        Generally preferred for More
                          supported CI/CD         credential-management
                          scenarios because it    overhead and risk if
                          removes the long-lived  the secret leaks
                          secret                  
  -----------------------------------------------------------------------

### Which one should you use?

**Prefer OIDC / workload identity federation** when it is supported and
can be configured for your Azure DevOps service connection. It removes
the need to manage a long-lived client secret.

Use **SP key authentication** when workload identity federation is not
available for the integration or environment, or when you have a
specific compatibility requirement. Protect the secret and establish a
rotation process.

------------------------------------------------------------------------

## 5. Azure permissions are separate from authentication

Authentication answers: **Who are you?**

Authorization answers: **What are you allowed to do?**

Both authentication methods identify the same service
principal/application identity if configured that way. The identity
still needs the appropriate Azure RBAC permissions.

For example, Terraform may need permissions to: - Read and create
resources in the target resource group. - Read networking resources. -
Access the Terraform remote-state storage account and container.

Grant only the permissions required by the pipeline. For remote state in
Azure Blob Storage, backend data-plane permissions may be required in
addition to permissions for managing infrastructure resources.

------------------------------------------------------------------------

## 6. Common troubleshooting checks

1.  **Confirm the service connection type.** Check whether it uses
    workload identity federation or a client secret.
2.  **Check `addSpnToEnvironment`.** It must be set to `true` if the
    script needs the exposed service-connection values.
3.  **Do not print credentials.** Avoid `echo "$servicePrincipalKey"` or
    `echo "$idToken"`.
4.  **Check Terraform environment variables.** Confirm the variables
    expected by your AzureRM provider version are set.
5.  **Check Azure RBAC.** A successful login does not mean the identity
    has permission to create resources or access the state storage.
6.  **Check subscription selection.** Ensure `ARM_SUBSCRIPTION_ID`
    points to the intended subscription.
7.  **Check provider documentation.** Authentication environment
    variables and OIDC behavior can vary by provider version.

------------------------------------------------------------------------

## 7. Quick mental model

-   `azureSubscription`: tells `AzureCLI@2` which Azure DevOps service
    connection to use.
-   `addSpnToEnvironment: true`: exposes the service connection's
    authentication information to the script.
-   **SP key**: Terraform authenticates using a client ID, tenant ID,
    and client secret.
-   **OIDC**: Terraform uses a short-lived federated token; no client
    secret is required.
-   **Azure RBAC**: determines what the authenticated identity can
    actually do.
