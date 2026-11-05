"""
Generate terraform.tfvars from Excel (.xlsx) configuration file.

Usage:
    python generate_tfvars.py --create-multisheet-xlsx ../config/process_config.xlsx
    python generate_tfvars.py --input ../config/process_config.xlsx
    python generate_tfvars.py --input ../config/process_config.xlsx --output ../terraform/terraform.tfvars
"""

import argparse
import os
import sys


# INFRA_DEFAULTS = {
#     'azure_region': 'germanywestcentral',
#     'vnet_name': 'vdf-dev01-vnet',
#     'vnet_resource_group': 'robotics-test',
#     'vnet_integration_subnet_name': 'vdf-dev01-subnet-funcoutboundsubnet',
#     'private_endpoint_subnet_name': 'vdf-dev01-subnet-private-endpoints',
#     'private_dns_zone_name': 'privatelink.azurewebsites.net',
#     'private_dns_zone_resource_group': 'robotics-test',
#     'webjobs_storage_account_name': 'stgwclambdatofunctionpoc',
#     'webjobs_storage_account_resource_group': 'robotics-test',
#     'log_analytics_workspace_name': 'vdf-prod-01-log-iass-getprocesses-v1',
#     'log_analytics_workspace_resource_group': 'robotics-test',
#     'global_key_vault_name': 'vdf-dev01-kv-gwc',
#     'global_key_vault_resource_group': 'robotics-test',
#     'local_key_vault_name': 'kv-lambdatofunctionpoc',
#     'local_key_vault_resource_group': 'robotics-test',
# }

INFRA_DEFAULTS_DEV = {
    'azure_region': 'germanywestcentral',
    'vnet_name': 'vnet-azugwc-140-90012-dev-001',
    'vnet_resource_group': 'rg-azugwc-90012-netw-dev-001',
    'vnet_integration_subnet_name': 'snet-azugwc-90012-lambda-loaders-egress-dev-001',
    'private_endpoint_subnet_name': 'snet-azugwc-90012-lambda-loaders-dev-001',
    'private_dns_zone_name': 'privatelink.azurewebsites.net',
    'private_dns_zone_resource_group': 'rg-azugwc-90012-netw-dev-001',
    'webjobs_storage_account_name': 'stgwclamlodev001',
    'webjobs_storage_account_resource_group': 'rg-azugwc-90012-sa-dev-001',
    'log_analytics_workspace_name': 'log-azugwc-90012-dev-001',
    'log_analytics_workspace_resource_group': 'rg-azugwc-90012-log-dev-001',
    'global_key_vault_name': 'kvgwcuipathdev001',
    'global_key_vault_resource_group': 'rg-azugwc-90012-kv-dev-001',
    'local_key_vault_name': 'kvgwclamlodev001',
    'local_key_vault_resource_group': 'rg-azugwc-90012-kv-dev-001',
    'confidentiality': 'C3',
    'managed_by': '',
    'project': 'Robotics and Automation Programme',
    'tagging_version': 'V2.4',
}

INFRA_DEFAULTS_PROD = {
    'azure_region': 'germanywestcentral',
    'vnet_name': 'vnet-azugwc-140-90012-prod-001',
    'vnet_resource_group': 'rg-azugwc-90012-netw-prod-001',
    'vnet_integration_subnet_name': 'snet-azugwc-90012-lambda-loaders-egress-prod-001',
    'private_endpoint_subnet_name': 'snet-azugwc-90012-lambda-loaders-prod-001',
    'private_dns_zone_name': 'privatelink.azurewebsites.net',
    'private_dns_zone_resource_group': 'rg-azugwc-90012-netw-prod-001',
    'webjobs_storage_account_name': 'stgwclamloprod001',
    'webjobs_storage_account_resource_group': 'rg-azugwc-90012-sa-prod-001',
    'log_analytics_workspace_name': 'log-azugwc-90012-prod-001',
    'log_analytics_workspace_resource_group': 'rg-azugwc-90012-log-prod-001',
    'global_key_vault_name': 'kvgwcuipathprod001',
    'global_key_vault_resource_group': 'rg-azugwc-90012-kv-prod-001',
    'local_key_vault_name': 'kvgwclamloprod001',
    'local_key_vault_resource_group': 'rg-azugwc-90012-kv-prod-001',
    'confidentiality': 'C3',
    'managed_by': '',
    'project': 'Robotics and Automation Programme',
    'tagging_version': 'V2.4',
}


def get_infra_defaults(environment):
    """Return the appropriate INFRA_DEFAULTS based on environment value."""
    env_lower = environment.lower() if environment else 'development'
    if env_lower in ('production', 'prod', 'hypercare'):
        return INFRA_DEFAULTS_PROD
    return INFRA_DEFAULTS_DEV

ENV_SHEET_CANDIDATES = [
    'FunctionAppEnvVars',
    'EnvironmentVariables',
    'Environment_Variables',
    'EnvVars',
]

KV_SHEET_CANDIDATES = [
    'KeyVaultSecrets',
    'KeyVault_Secrets',
    'KVSecrets',
]

ENV_TO_CONFIG_MAP = {
    'SERVICE_NAME': 'service_name',
    'PROCESS_NAME': 'process_name',
    'PROCESS_FUNCTION': 'function',
    'CASE_LIMIT': 'case_limit',
    'QUEUE_NAME': 'queue_name',
    'SHORT_DESCRIPTION': 'short_description',
    'ORCHESTRATOR_ENVIRONMENT': 'orchestrator_environment',
    'PROCESS_IDENTIFIER': 'process_identifier',
    'PROJECT_NAME': 'project_name',
    'PROCESS_STAGE': 'process_stage',
    'SCHEDULE_CRON': 'schedule_cron',
}

ENV_CONFIG_KEYS = [
    'service_name',
    'function',
    'case_limit',
    'queue_name',
    'short_description',
    'orchestrator_environment',
    'process_identifier',
    'project_name',
    'process_stage',
    'schedule_cron',
]

KV_SECRET_CONFIG_KEYS = [
    'global_key_vault_secret_names',
    'local_key_vault_secret_names',
    'local_key_vault_secret_access',
]

TAG_CONFIG_KEYS = [
    ('confidentiality', 'C3', 'Tag: Data classification'),
    ('managed_by', '', 'Tag: Owner email'),
    ('project', 'Robotics and Automation Programme', 'Tag: Project name'),
    ('tagging_version', 'V2.4', 'Tag: Tagging version'),
]

EXCLUDED_FROM_CONFIG_SHEET = ['description']

ENV_ROW_DEFINITIONS = [
    ('SERVICE_NAME', 'service_name', 'Service identifier'),
    ('PROCESS_FUNCTION', 'function', 'Function type'),
    ('CASE_LIMIT', 'case_limit', 'Max cases per execution'),
    ('QUEUE_NAME', 'queue_name', 'UiPath work queue name'),
    ('SHORT_DESCRIPTION', 'short_description', 'Process short description'),
    ('ORCHESTRATOR_ENVIRONMENT', 'orchestrator_environment', 'UiPath orchestrator environment'),
    ('PROCESS_IDENTIFIER', 'process_identifier', 'Process identifier for UiPath'),
    ('PROJECT_NAME', 'project_name', 'Project name for UiPath'),
    ('PROCESS_STAGE', 'process_stage', 'Process stage (loader/dispatcher/performer)'),
    ('SCHEDULE_CRON', 'schedule_cron', 'Timer trigger NCRONTAB schedule (e.g. 0 */15 * * * *)'),
]


def parse_list_value(raw_value):
    """Parse CSV list-style value separated by ; or , into a list of strings."""
    if not raw_value:
        return []
    normalized = raw_value.replace(',', ';')
    return [item.strip() for item in normalized.split(';') if item.strip()]


def _require_openpyxl():
    try:
        from openpyxl import load_workbook, Workbook
        return load_workbook, Workbook
    except ImportError:
        print('ERROR: openpyxl is required to read or write Excel files.')
        print('Install it with: pip install openpyxl')
        sys.exit(1)


def _normalize_header(value):
    return str(value or '').strip().lower().replace('_', ' ')


def _find_sheet(workbook, candidates):
    sheet_map = {name.lower(): name for name in workbook.sheetnames}
    for candidate in candidates:
        match = sheet_map.get(candidate.lower())
        if match:
            return workbook[match]
    return None


def _read_kv_sheet(ws):
    headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
    normalized = [_normalize_header(h) for h in headers]

    name_idx = None
    type_idx = None
    access_idx = None
    for i, h in enumerate(normalized):
        if h in ['parameter name', 'name', 'secret name', 'parameter']:
            name_idx = i
        if h in ['type', 'scope', 'secret type']:
            type_idx = i
        if h in ['functionappidentity access', 'function app identity access', 'function app identityaccess', 'function app access', 'access']:
            access_idx = i

    if name_idx is None or type_idx is None:
        raise ValueError(
            "KeyVaultSecrets sheet must contain columns for parameter name and type (Global/Local)."
        )

    global_secrets = []
    local_secrets = []
    local_secret_access = {}
    for row in ws.iter_rows(min_row=2):
        secret_name = str(row[name_idx].value or '').strip()
        secret_type = str(row[type_idx].value or '').strip().lower()

        if not secret_name:
            continue

        if secret_type == 'global':
            global_secrets.append(secret_name)
        elif secret_type == 'local':
            secret_access = 'read'
            if access_idx is not None:
                raw_access = str(row[access_idx].value or '').strip().lower()
                if raw_access:
                    secret_access = raw_access

            if secret_access not in ['read', 'write']:
                raise ValueError(
                    f"Invalid FunctionAppIdentity access '{secret_access}' for local secret '{secret_name}'. Use read or write."
                )

            local_secrets.append(secret_name)
            local_secret_access[secret_name] = secret_access
        else:
            raise ValueError(
                f"Invalid KeyVault secret type '{row[type_idx].value}' for '{secret_name}'. Use Global or Local."
            )

    return global_secrets, local_secrets, local_secret_access


def _read_env_sheet(ws):
    headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
    normalized = [_normalize_header(h) for h in headers]

    name_idx = None
    value_idx = None
    for i, h in enumerate(normalized):
        if h in ['environment variable name', 'env var name', 'name', 'variable name', 'key']:
            name_idx = i
        if h in ['value', 'default value']:
            value_idx = i

    if name_idx is None or value_idx is None:
        raise ValueError(
            "FunctionAppEnvVars sheet must contain columns for environment variable name and value."
        )

    resolved = {}
    custom_env_vars = {}
    for row in ws.iter_rows(min_row=2):
        env_name = str(row[name_idx].value or '').strip()
        env_value = str(row[value_idx].value or '').strip()

        if not env_name:
            continue

        mapped_key = ENV_TO_CONFIG_MAP.get(env_name.upper())
        if mapped_key:
            resolved[mapped_key] = env_value
            continue

        # Also accept direct tfvars keys in the env sheet.
        env_key = env_name.strip().lower()
        if env_key in [
            'service_name', 'function', 'case_limit', 'queue_name',
            'short_description', 'orchestrator_environment',
            'process_identifier', 'project_name', 'process_stage',
            'process_name', 'schedule_cron'
        ]:
            resolved[env_key] = env_value
        else:
            # Any other env var is a custom/dynamic one
            custom_env_vars[env_name] = env_value

    return resolved, custom_env_vars


def _load_template_rows():
    """Load template rows from the Config sheet of the template XLSX if available."""
    load_workbook, _ = _require_openpyxl()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_xlsx = os.path.join(script_dir, '..', 'config', 'process_config_template.xlsx')
    template_xlsx = os.path.abspath(template_xlsx)

    rows = []
    if not os.path.exists(template_xlsx):
        # Hardcoded default template when no template XLSX exists
        return [
            {'Parameter': 'environment', 'Value': 'production', 'Description': 'Environment: development / hypercare / production'},
            {'Parameter': 'product', 'Value': 'vdf', 'Description': 'Product/project prefix identifier'},
            {'Parameter': 'local_market', 'Value': '', 'Description': 'Country/market code (e.g., DE, UK, ES)'},
            {'Parameter': 'business_vertical', 'Value': '', 'Description': 'Business unit identifier'},
            {'Parameter': 'process_name', 'Value': '', 'Description': 'Automation/process name'},
            {'Parameter': 'shortcode', 'Value': '', 'Description': '3-4 character application shortcode'},
            {'Parameter': 'node_version', 'Value': '24', 'Description': 'Node.js version for the function runtime'},
            {'Parameter': 'memory_mb', 'Value': '512', 'Description': 'Function memory allocation in MB (512 / 2048 / 4096)'},
            {'Parameter': 'timeout_seconds', 'Value': '900', 'Description': 'Function timeout in seconds'},
            {'Parameter': 'resource_group_name', 'Value': '', 'Description': 'Leave empty for auto-generated name'},
            {'Parameter': 'process_storage_account_name', 'Value': '', 'Description': 'Existing process storage account name (optional)'},
            {'Parameter': 'process_storage_account_resource_group', 'Value': '', 'Description': 'Resource group for process storage account (required if name provided)'},
            {'Parameter': 'application_insights_name', 'Value': '', 'Description': 'Existing Application Insights resource name'},
            {'Parameter': 'application_insights_resource_group', 'Value': '', 'Description': 'Resource group containing existing Application Insights'},
            {'Parameter': 'service_name', 'Value': '', 'Description': 'Service identifier'},
            {'Parameter': 'function', 'Value': '', 'Description': 'Function type'},
            {'Parameter': 'case_limit', 'Value': '5', 'Description': 'Max cases per execution'},
            {'Parameter': 'queue_name', 'Value': '', 'Description': 'UiPath work queue name'},
            {'Parameter': 'short_description', 'Value': '', 'Description': 'Process short description'},
            {'Parameter': 'orchestrator_environment', 'Value': 'production', 'Description': 'UiPath orchestrator environment'},
            {'Parameter': 'process_identifier', 'Value': '', 'Description': 'Process identifier for UiPath'},
            {'Parameter': 'project_name', 'Value': '', 'Description': 'Project name for UiPath'},
            {'Parameter': 'process_stage', 'Value': 'loader', 'Description': 'Process stage (loader/dispatcher/performer)'},
            {'Parameter': 'schedule_cron', 'Value': '0 */15 * * * *', 'Description': 'Timer trigger NCRONTAB schedule'},
            {'Parameter': 'global_key_vault_secret_names', 'Value': '', 'Description': 'Comma separated list of global KV secret names'},
            {'Parameter': 'local_key_vault_secret_names', 'Value': '', 'Description': 'Comma separated list of local KV secret names'},
        ]

    wb = load_workbook(template_xlsx, read_only=True)
    ws = wb['Config'] if 'Config' in wb.sheetnames else wb.active

    headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
    param_idx = headers.index('Parameter')
    value_idx = headers.index('Value')
    desc_idx = headers.index('Description') if 'Description' in headers else None

    for row in ws.iter_rows(min_row=2):
        param = str(row[param_idx].value or '').strip()
        value = str(row[value_idx].value or '').strip()
        desc = str(row[desc_idx].value or '').strip() if desc_idx is not None else ''
        if param:
            rows.append({'Parameter': param, 'Value': value, 'Description': desc})

    wb.close()
    return rows


def create_multisheet_xlsx(output_path, seed_config):
    _, Workbook = _require_openpyxl()

    wb = Workbook()
    ws_config = wb.active
    ws_config.title = 'Config'
    ws_env = wb.create_sheet('FunctionAppEnvVars')
    ws_kv = wb.create_sheet('KeyVaultSecrets')

    template_rows = _load_template_rows()
    template_defaults = {row['Parameter']: row['Value'] for row in template_rows if row['Parameter']}

    tag_keys = [t[0] for t in TAG_CONFIG_KEYS]

    ws_config.append(['Parameter', 'Value', 'Description'])
    for row in template_rows:
        parameter = row['Parameter']
        if not parameter:
            continue
        if parameter in ENV_CONFIG_KEYS or parameter in KV_SECRET_CONFIG_KEYS:
            continue
        if parameter in tag_keys or parameter in EXCLUDED_FROM_CONFIG_SHEET:
            continue

        seeded_value = seed_config.get(parameter)
        value = seeded_value if seeded_value is not None else row['Value']
        ws_config.append([parameter, value, row['Description']])

    # Append tag values at the bottom
    for tag_key, tag_default, tag_desc in TAG_CONFIG_KEYS:
        seeded_value = seed_config.get(tag_key)
        value = seeded_value if seeded_value is not None else tag_default
        ws_config.append([tag_key, value, tag_desc])

    ws_env.append(['Environment Variable Name', 'Value', 'Description'])
    for env_name, config_key, description in ENV_ROW_DEFINITIONS:
        seeded_value = seed_config.get(config_key)
        default_value = template_defaults.get(config_key, '')
        value = seeded_value if seeded_value is not None else default_value
        ws_env.append([env_name, value, description])

    ws_kv.append(['Parameter Name', 'Type', 'FunctionAppIdentity access', 'Description'])
    global_raw = seed_config.get('global_key_vault_secret_names', template_defaults.get('global_key_vault_secret_names', ''))
    local_raw = seed_config.get('local_key_vault_secret_names', template_defaults.get('local_key_vault_secret_names', ''))

    global_secrets = parse_list_value(global_raw)
    local_secrets = parse_list_value(local_raw)

    if global_secrets:
        for secret_name in global_secrets:
            ws_kv.append([secret_name, 'Global', 'read', 'Global Key Vault secret'])
    else:
        ws_kv.append(['', 'Global', 'read', 'Global Key Vault secret'])

    if local_secrets:
        for secret_name in local_secrets:
            ws_kv.append([secret_name, 'Local', 'read', 'Local Key Vault secret'])
    else:
        ws_kv.append(['', 'Local', 'read', 'Local Key Vault secret'])

    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    wb.save(output_path)
    print(f'Created multi-sheet config workbook: {output_path}')

def read_excel(file_path):
    """Read configuration from Excel file."""
    load_workbook, _ = _require_openpyxl()

    config = {}
    wb = load_workbook(file_path, read_only=True)
    core_ws = wb['Config'] if 'Config' in wb.sheetnames else wb.active

    headers = [cell.value for cell in next(core_ws.iter_rows(min_row=1, max_row=1))]
    param_idx = headers.index('Parameter')
    value_idx = headers.index('Value')

    for row in core_ws.iter_rows(min_row=2):
        key = row[param_idx].value
        value = row[value_idx].value
        if key:
            config[key.strip()] = str(value).strip() if value else ''

    env_ws = _find_sheet(wb, ENV_SHEET_CANDIDATES)
    if env_ws is not None:
        env_resolved, custom_env_vars = _read_env_sheet(env_ws)
        config.update(env_resolved)
        config['_custom_env_vars'] = custom_env_vars

    kv_ws = _find_sheet(wb, KV_SHEET_CANDIDATES)
    if kv_ws is not None:
        global_secrets, local_secrets, local_secret_access = _read_kv_sheet(kv_ws)
        config['global_key_vault_secret_names'] = ';'.join(global_secrets)
        config['local_key_vault_secret_names'] = ';'.join(local_secrets)
        config['_local_key_vault_secret_access'] = local_secret_access

    wb.close()
    return config


def validate_config(config):
    """Validate required configuration parameters."""
    required_fields = [
        'environment', 'product', 'local_market', 'business_vertical',
        'process_name', 'shortcode',
        'schedule_cron',
        'application_insights_name', 'application_insights_resource_group'
    ]

    errors = []
    for field in required_fields:
        if field not in config or not config[field]:
            errors.append(f"Missing required field: {field}")

    # Validate environment
    valid_envs = ['development', 'hypercare', 'production']
    if config.get('environment', '').lower() not in valid_envs:
        errors.append(f"Invalid environment: '{config.get('environment')}'. Must be one of: {valid_envs}")

    # Validate boolean fields
    bool_fields = []
    for field in bool_fields:
        if config.get(field, '').lower() not in ['true', 'false', '']:
            errors.append(f"Invalid boolean value for {field}: '{config.get(field)}'. Must be true/false")

    memory_value = config.get('memory_mb', '512').strip()
    if memory_value:
        try:
            memory_mb = int(memory_value)
        except ValueError:
            errors.append(f"Invalid numeric value for memory_mb: '{memory_value}'.")
        else:
            if memory_mb not in [512, 2048, 4096]:
                errors.append("Invalid value for memory_mb. For Flex Consumption it must be one of: 512, 2048, 4096.")

    infra = get_infra_defaults(config.get('environment', 'development'))
    storage_required = ['webjobs_storage_account_name', 'webjobs_storage_account_resource_group']
    for field in storage_required:
        effective_value = config.get(field) or infra.get(field)
        if not effective_value:
            errors.append(f"Missing required field: {field}")

    process_sa_name = config.get('process_storage_account_name', '').strip()
    process_sa_rg = config.get('process_storage_account_resource_group', '').strip()
    if process_sa_name and not process_sa_rg:
        errors.append("Missing process_storage_account_resource_group when process_storage_account_name is provided")

    # Validate secret list format (optional but must parse cleanly)
    try:
        parse_list_value(config.get('global_key_vault_secret_names', ''))
        parse_list_value(config.get('local_key_vault_secret_names', ''))
    except Exception as ex:
        errors.append(f"Invalid secret list format: {ex}")

    for secret_name, access in config.get('_local_key_vault_secret_access', {}).items():
        if str(access).strip().lower() not in ['read', 'write']:
            errors.append(
                f"Invalid FunctionAppIdentity access '{access}' for local secret '{secret_name}'. Use read or write."
            )

    if errors:
        print("Configuration validation failed:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    print("Configuration validation passed.")


def generate_tfvars(config, output_path):
    """Generate terraform.tfvars file from configuration."""

    # Determine environment suffix
    env = config.get('environment', 'development').lower()
    env_suffix = 'dev' if env == 'development' else 'prod'

    # Select infra defaults based on environment
    infra = get_infra_defaults(env)

    # Auto-generate resource group name if not provided
    rg_name = config.get('resource_group_name', '')
    if not rg_name:
        rg_name = f"{config['product']}-{env_suffix}-rg-{config['shortcode']}-loader"

    # Keep pipeline metadata aligned with terraform/locals.tf.
    process_name_slug = config['process_name'].lower().replace('_', '-').replace(' ', '-')
    func_name = f"func-azugwc-{process_name_slug}-{env_suffix}-001"

    lines = []
    lines.append('# Auto-generated terraform.tfvars')
    lines.append(f'# Generated for: {config.get("process_name", "unknown")}')
    lines.append(f'# Environment: {env}')
    lines.append('')
    lines.append('# ===== General =====')
    lines.append(f'environment          = "{env}"')
    lines.append(f'product              = "{config.get("product", "vdf")}"')
    lines.append(f'azure_region         = "{infra["azure_region"]}"')
    lines.append(f'resource_group_name  = "{rg_name}"')
    lines.append('')
    lines.append('# ===== Application Identity =====')
    lines.append(f'process_name         = "{config.get("process_name", "")}"')
    lines.append(f'shortcode            = "{config.get("shortcode", "")}"')
    lines.append(f'local_market         = "{config.get("local_market", "")}"')
    lines.append(f'business_vertical    = "{config.get("business_vertical", "")}"')
    lines.append('')
    lines.append('# ===== Function App Configuration =====')
    lines.append(f'function_app_name    = "{func_name}"')
    lines.append('zone_redundancy_enabled = true')
    lines.append(f'node_version         = "{config.get("node_version", "18")}"')
    lines.append(f'memory_mb            = {config.get("memory_mb", "512")}')
    lines.append(f'timeout_seconds      = {config.get("timeout_seconds", "900")}')
    lines.append(f'schedule_cron        = "{config.get("schedule_cron", "0 */15 * * * *")}"')
    lines.append('reserved_instances   = 1')
    lines.append('')
    lines.append('# ===== Networking =====')
    lines.append(f'vnet_name            = "{infra["vnet_name"]}"')
    lines.append(f'vnet_resource_group  = "{infra["vnet_resource_group"]}"')
    lines.append(f'vnet_integration_subnet_name = "{infra["vnet_integration_subnet_name"]}"')
    lines.append(f'private_endpoint_subnet_name = "{infra["private_endpoint_subnet_name"]}"')
    lines.append(f'private_dns_zone_name = "{infra["private_dns_zone_name"]}"')
    lines.append(f'private_dns_zone_resource_group = "{infra["private_dns_zone_resource_group"]}"')
    lines.append(f'webjobs_storage_account_name = "{infra["webjobs_storage_account_name"]}"')
    lines.append(f'webjobs_storage_account_resource_group = "{infra["webjobs_storage_account_resource_group"]}"')
    lines.append(f'process_storage_account_name = "{config.get("process_storage_account_name", "")}"')
    lines.append(f'process_storage_account_resource_group = "{config.get("process_storage_account_resource_group", "")}"')
    lines.append(f'log_analytics_workspace_name = "{infra["log_analytics_workspace_name"]}"')
    lines.append(f'log_analytics_workspace_resource_group = "{infra["log_analytics_workspace_resource_group"]}"')
    lines.append(f'application_insights_name = "{config.get("application_insights_name", "")}"')
    lines.append(f'application_insights_resource_group = "{config.get("application_insights_resource_group", "")}"')
    lines.append(f'global_key_vault_name = "{infra["global_key_vault_name"]}"')
    lines.append(f'global_key_vault_resource_group = "{infra["global_key_vault_resource_group"]}"')
    lines.append(f'local_key_vault_name = "{infra["local_key_vault_name"]}"')
    lines.append(f'local_key_vault_resource_group = "{infra["local_key_vault_resource_group"]}"')

    global_secret_names = parse_list_value(config.get("global_key_vault_secret_names", ""))
    local_secret_names = parse_list_value(config.get("local_key_vault_secret_names", ""))
    local_secret_access = config.get('_local_key_vault_secret_access', {})
    global_hcl = ", ".join([f'"{name}"' for name in global_secret_names])
    local_hcl = ", ".join([f'"{name}"' for name in local_secret_names])
    lines.append(f'global_key_vault_secret_names = [{global_hcl}]')
    lines.append(f'local_key_vault_secret_names = [{local_hcl}]')

    lines.append('local_key_vault_secret_access = {')
    for name in local_secret_names:
        access_value = str(local_secret_access.get(name, 'read')).strip().lower() or 'read'
        escaped_name = name.replace('\\', '\\\\').replace('"', '\\"')
        lines.append(f'  "{escaped_name}" = "{access_value}"')
    lines.append('}')
    lines.append('')
    lines.append('# ===== Process Configuration (Environment Variables) =====')
    lines.append(f'service_name                = "{config.get("service_name", "")}"')
    lines.append(f'process_function            = "{config.get("function", "")}"')
    lines.append(f'case_limit                  = "{config.get("case_limit", "5")}"')
    lines.append(f'queue_name                  = "{config.get("queue_name", "")}"')
    lines.append(f'short_description           = "{config.get("short_description", "")}"')
    lines.append(f'orchestrator_environment    = "{config.get("orchestrator_environment", "hypercare")}"')
    lines.append(f'process_identifier          = "{config.get("process_identifier", "")}"')
    lines.append(f'project_name                = "{config.get("project_name", "")}"')
    lines.append(f'process_stage               = "{config.get("process_stage", "")}"')
    lines.append('')
    lines.append('# ===== Custom Environment Variables =====')
    custom_env_vars = config.get('_custom_env_vars', {})
    if custom_env_vars:
        lines.append('custom_app_settings = {')
        for key, value in custom_env_vars.items():
            escaped_value = value.replace('\\', '\\\\').replace('"', '\\"')
            lines.append(f'  {key} = "{escaped_value}"')
        lines.append('}')
    else:
        lines.append('custom_app_settings = {}')
    lines.append('')
    lines.append('# ===== Tags =====')
    lines.append(f'confidentiality      = "{infra["confidentiality"]}"')
    lines.append(f'managed_by           = "{infra["managed_by"]}"')
    lines.append(f'project              = "{infra["project"]}"')
    lines.append(f'tagging_version      = "{infra["tagging_version"]}"')

    tfvars_content = '\n'.join(lines) + '\n'

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(tfvars_content)

    print(f"Generated: {output_path}")


def generate_function_code(config, process_dir):
    """Generate reference/reference.txt with Key Vault secret retrieval scaffold."""

    ref_dir = os.path.join(process_dir, 'reference')
    os.makedirs(ref_dir, exist_ok=True)

    process_name = config.get('process_name', 'ProcessName')

    # Parse secret names
    global_secrets = parse_list_value(config.get('global_key_vault_secret_names', ''))
    local_secrets = parse_list_value(config.get('local_key_vault_secret_names', ''))
    all_secrets = [(s, 'global') for s in global_secrets] + [(s, 'local') for s in local_secrets]

    # --- Generate reference.txt ---
    index_lines = []
    index_lines.append("const { KeyVault } = require('./services/key-vault');")
    index_lines.append("const { Logger } = require('./services/logger');")
    index_lines.append("const logging = new Logger();")
    index_lines.append("")
    index_lines.append("")
    index_lines.append("//-------------------------------- Process Definition Parameters -----------------------------//")
    index_lines.append(f'const serviceName = process.env.SERVICE_NAME || "{config.get("service_name", "")}";')
    index_lines.append(f'const functionName = process.env.PROCESS_FUNCTION || "{config.get("function", "")}";')
    index_lines.append(f'const processStage = process.env.PROCESS_STAGE || "{config.get("process_stage", "Loader")}";')
    index_lines.append(f'const processName = process.env.PROCESS_NAME || "{process_name}";')
    index_lines.append(f'const projectName = process.env.PROJECT_NAME || "{config.get("project_name", "")}";')
    index_lines.append(f'const processIdentifier = process.env.PROCESS_IDENTIFIER || "{config.get("process_identifier", "")}";')
    index_lines.append(f'const localMarket = process.env.LOCAL_MARKET || "{config.get("local_market", "")}";')
    index_lines.append("")
    index_lines.append("")
    index_lines.append("// Get the needed secret parameter names from environment variables")

    # Generate env var declarations for each secret
    for secret_name, _scope in all_secrets:
        env_var_name = secret_name.replace('-', '_').replace(' ', '_')
        index_lines.append(f"const {env_var_name}ParameterName = process.env.{env_var_name}ParameterName || '{secret_name}';")

    index_lines.append("")
    index_lines.append("")
    index_lines.append("// -------------------------------->  Main Handler  <-------------------------------- //")
    index_lines.append("exports.handler = async function(event, context) {")
    index_lines.append("")
    index_lines.append("    try {")
    index_lines.append("")
    index_lines.append("        context = {")
    index_lines.append("            ...context,")
    index_lines.append("            processIdentifier,")
    index_lines.append("            serviceName,")
    index_lines.append("            functionName,")
    index_lines.append("            projectName,")
    index_lines.append("            localMarket,")
    index_lines.append("            processStage,")
    index_lines.append("            processName")
    index_lines.append("        };")
    index_lines.append("")
    index_lines.append("        const keyVault = new KeyVault();")
    index_lines.append("")
    index_lines.append("")
    index_lines.append("        // -----------------------------> Retrieve parameters from Key Vault <----------------------------- //")

    # Generate Key Vault retrieval calls
    for secret_name, _scope in all_secrets:
        env_var_name = secret_name.replace('-', '_').replace(' ', '_')
        index_lines.append(f"        const {env_var_name} = await keyVault.getSecret({env_var_name}ParameterName);")

    index_lines.append("")
    index_lines.append("")
    index_lines.append("        // -----------------------------> Main Flow <----------------------------- //")
    index_lines.append("")
    index_lines.append('        logging.logger("Process Started", false, context);')
    index_lines.append("")
    index_lines.append("        // TODO: Implement process logic here")
    index_lines.append("")
    index_lines.append('        logging.logger("Process Ended", false, context);')
    index_lines.append("")
    index_lines.append("        return 0;")
    index_lines.append("")
    index_lines.append("    }")
    index_lines.append("    catch (err) {")
    index_lines.append("")
    index_lines.append("        console.error(err);")
    index_lines.append('        logging.logger(err.message, true, context);')
    index_lines.append("        throw err;")
    index_lines.append("")
    index_lines.append("    }")
    index_lines.append("")
    index_lines.append("};")
    index_lines.append("")

    _write_file(os.path.join(ref_dir, 'reference.txt'), '\n'.join(index_lines))

    print(f"Generated reference/reference.txt at: {ref_dir}")


def _write_file(file_path, content):
    """Write content to file, creating parent dirs if needed. Skip if file already exists."""
    if os.path.exists(file_path):
        print(f"  Skipped (already exists): {file_path}")
        return
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  Created: {file_path}")


def main():
    parser = argparse.ArgumentParser(description='Generate terraform.tfvars from Excel (.xlsx) config')
    parser.add_argument('--input', '-i', required=False, help='Path to Excel (.xlsx) config file')
    parser.add_argument('--output', '-o', default=None, help='Output path for terraform.tfvars')
    parser.add_argument(
        '--create-multisheet-xlsx',
        default=None,
        help='Create a multi-sheet Excel config file (Config, FunctionAppEnvVars, KeyVaultSecrets) and exit',
    )
    args = parser.parse_args()

    if args.create_multisheet_xlsx:
        create_output = os.path.abspath(args.create_multisheet_xlsx)
        create_multisheet_xlsx(create_output, {})
        return

    if not args.input:
        parser.error('--input is required unless --create-multisheet-xlsx is used')

    input_path = os.path.abspath(args.input)
    if not os.path.exists(input_path):
        print(f"ERROR: Input file not found: {input_path}")
        sys.exit(1)

    ext = os.path.splitext(input_path)[1].lower()
    if ext not in ['.xlsx', '.xls']:
        print(f"ERROR: Unsupported file format: {ext}. Use .xlsx")
        sys.exit(1)

    config = read_excel(input_path)

    # Validate
    validate_config(config)

    # Determine output path
    if args.output:
        output_path = os.path.abspath(args.output)
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(script_dir, '..', 'terraform', 'terraform.tfvars')
        output_path = os.path.abspath(output_path)

    # Generate
    generate_tfvars(config, output_path)

    # Generate functionCode scaffold under the process directory
    # input_path is <processName>/config/<env>/process_config.xlsx, so go up two levels
    process_dir = os.path.join(os.path.dirname(input_path), '..', '..')
    process_dir = os.path.abspath(process_dir)
    generate_function_code(config, process_dir)

    print("Done! Run 'terraform plan' to preview changes.")


if __name__ == '__main__':
    main()
