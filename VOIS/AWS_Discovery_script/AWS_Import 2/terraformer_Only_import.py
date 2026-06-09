import subprocess
import os
import glob
import shutil
import re
import json
import datetime
import sys


# ---------------------------------------------------------------------------
# Run Logger — tees all print() output to a timestamped log file
# ---------------------------------------------------------------------------

class RunLogger:
    """Tees stdout to both the console and a log file simultaneously."""

    def __init__(self, log_path):
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        self.log_path = log_path
        self._log_file = open(log_path, 'w', encoding='utf-8')
        self._original_stdout = sys.stdout
        sys.stdout = self
        self._log_file.write(f"# Import run started: {datetime.datetime.utcnow().isoformat()}Z\n\n")

    def write(self, message):
        self._original_stdout.write(message)
        self._log_file.write(message)

    def flush(self):
        self._original_stdout.flush()
        self._log_file.flush()

    def close(self):
        sys.stdout = self._original_stdout
        self._log_file.write(f"\n# Import run ended: {datetime.datetime.utcnow().isoformat()}Z\n")
        self._log_file.close()
        # Restore stdout first, then print so the message goes to console
        print(f"\n📄 Run log saved: {self.log_path}")


def build_terraformer_env():
    """Build environment for Terraformer with a valid HOME on Windows."""
    env = os.environ.copy()
    user_home = env.get('USERPROFILE') or os.path.expanduser('~')
    if user_home:
        env.setdefault('USERPROFILE', user_home)
        env['HOME'] = env.get('HOME') or user_home
    return env


def sanitize_name(value):
    """Create a filesystem-safe segment for account/app names."""
    sanitized = re.sub(r'[^A-Za-z0-9._-]+', '-', value.strip())
    return sanitized.strip('-') or 'default'


def get_legacy_plugin_dir(env):
    """Return Terraformer's legacy plugin directory on Windows."""
    home = env.get('HOME') or env.get('USERPROFILE') or os.path.expanduser('~')
    return os.path.join(home, '.terraform.d', 'plugins', 'windows_amd64')


def get_provider_search_roots(bootstrap_dir, env):
    """Return directories that may contain Terraform-downloaded provider binaries."""
    roots = [os.path.join(bootstrap_dir, '.terraform')]

    plugin_cache_dir = env.get('TF_PLUGIN_CACHE_DIR', '').strip()
    if plugin_cache_dir:
        roots.append(plugin_cache_dir)

    cli_config_file = env.get('TF_CLI_CONFIG_FILE', '').strip()
    if cli_config_file and os.path.isfile(cli_config_file):
        try:
            with open(cli_config_file, 'r', encoding='utf-8') as config_file:
                config_text = config_file.read()
        except OSError:
            config_text = ''

        match = re.search(r'plugin_cache_dir\s*=\s*"([^"]+)"', config_text)
        if match:
            roots.append(os.path.expandvars(match.group(1)))

    unique_roots = []
    for root in roots:
        normalized = os.path.normcase(os.path.normpath(root))
        if normalized not in unique_roots:
            unique_roots.append(normalized)

    return [root for root in roots if os.path.isdir(root)]


def find_aws_provider_binary(search_roots):
    """Find a Terraform-downloaded AWS provider executable in known roots."""
    patterns = [
        os.path.join('**', 'terraform-provider-aws*.exe'),
        os.path.join('**', 'terraform-provider-aws*'),
    ]

    for root in search_roots:
        for pattern in patterns:
            matches = glob.glob(os.path.join(root, pattern), recursive=True)
            files = [match for match in matches if os.path.isfile(match)]
            if files:
                files.sort(key=lambda item: (('registry.terraform.io' not in item.lower()), len(item)))
                return files[0]

    return None


def ensure_aws_provider_plugin(env):
    """Ensure Terraformer can find terraform-provider-aws on Windows."""
    plugin_dir = get_legacy_plugin_dir(env)
    os.makedirs(plugin_dir, exist_ok=True)

    existing = glob.glob(os.path.join(plugin_dir, 'terraform-provider-aws*.exe'))
    if existing:
        print(f"✓ AWS provider plugin found: {os.path.basename(existing[0])}")
        return True

    print("AWS provider plugin not found in Terraformer legacy path.")
    print("Bootstrapping provider via Terraform init...")

    bootstrap_dir = os.path.join(os.getcwd(), '.tf-provider-bootstrap')
    os.makedirs(bootstrap_dir, exist_ok=True)
    bootstrap_tf = os.path.join(bootstrap_dir, 'main.tf')

    with open(bootstrap_tf, 'w', encoding='ascii') as f:
        f.write(
            'terraform {\n'
            '  required_providers {\n'
            '    aws = {\n'
            '      source  = "hashicorp/aws"\n'
            '      version = "~> 5.0"\n'
            '    }\n'
            '  }\n'
            '}\n'
        )

    init_cmd = ['terraform', 'init', '-input=false']
    init_result = subprocess.run(init_cmd, cwd=bootstrap_dir, capture_output=True, text=True, env=env)
    if init_result.returncode != 0:
        print("✗ Failed to bootstrap AWS provider plugin")
        print((init_result.stderr or init_result.stdout or '').strip())
        return False

    search_roots = get_provider_search_roots(bootstrap_dir, env)
    provider_bin = find_aws_provider_binary(search_roots)

    if not provider_bin:
        print("✗ Terraform init completed, but no AWS provider executable was found")
        if search_roots:
            print("Checked these locations:")
            for root in search_roots:
                print(f"  - {root}")
        return False

    destination = os.path.join(plugin_dir, os.path.basename(provider_bin))
    shutil.copy2(provider_bin, destination)
    print(f"✓ Installed AWS provider plugin to {destination}")
    return True


def run_cmd(cmd, env, cwd=None):
    """Run command and return subprocess result."""
    return subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=cwd)


def check_terraformer_installed(env):
    """Check if terraformer is installed."""
    try:
        result = run_cmd(['terraformer', 'version'], env)
        if result.returncode == 0:
            print("✓ Terraformer is installed")
            print(result.stdout.strip())
            return True
    except FileNotFoundError:
        pass

    print("✗ Terraformer is not installed")
    return False


def check_aws_cli_installed(env):
    """Check if AWS CLI is installed."""
    try:
        result = run_cmd(['aws', '--version'], env)
        if result.returncode == 0:
            print("✓ AWS CLI is installed")
            return True
    except FileNotFoundError:
        pass

    print("✗ AWS CLI is not installed or not on PATH")
    return False


def check_aws_provider_supported(env):
    """Check if current terraformer binary supports AWS provider."""
    result = run_cmd(['terraformer', 'import', '--help'], env)
    help_text = f"{result.stdout}\n{result.stderr}".lower()
    if 'aws' in help_text:
        return True

    print("✗ Current Terraformer installation does not include AWS provider support")
    print("Run 'terraformer import --help' to see available providers in your binary")
    return False


# ---------------------------------------------------------------------------
# Secure Authentication — AWS Secrets Manager
# ---------------------------------------------------------------------------

def authenticate_from_secrets_manager(account, env):
    """Retrieve AWS credentials from Secrets Manager and return an authenticated env.

    Uses a local AWS CLI profile (with minimal secretsmanager:GetSecretValue permission)
    to fetch credentials stored in a Secrets Manager secret.

    Account config fields:
      secret_name  (required) — Name or ARN of the Secrets Manager secret
      profile      (required) — AWS CLI profile with access to Secrets Manager
      region       (optional) — Region where the secret is stored (default: us-east-1)

    Expected secret JSON format:
      {"aws_access_key_id": "AKIA...", "aws_secret_access_key": "..."}

    Returns environment dict with credentials injected, or None on failure.
    """
    secret_name = account.get('secret_name')
    profile = account.get('profile', 'default')
    secret_region = account.get('secret_region', 'us-east-1')

    if not secret_name:
        print("  ✗ 'secret_name' is required in account config")
        return None

    print(f"  🔐 Retrieving credentials from Secrets Manager")
    print(f"     Secret: {secret_name}")
    print(f"     Profile: {profile}")

    cmd = [
        'aws', 'secretsmanager', 'get-secret-value',
        '--secret-id', secret_name,
        '--profile', profile,
        '--region', secret_region,
        '--query', 'SecretString',
        '--output', 'text',
    ]

    result = run_cmd(cmd, env)
    if result.returncode != 0:
        error_msg = (result.stderr or result.stdout or '').strip()
        print(f"  ✗ Failed to retrieve secret:")
        print(f"    {error_msg}")
        return None

    # Parse the secret JSON
    try:
        secret_data = json.loads(result.stdout.strip())
    except (json.JSONDecodeError, ValueError):
        print("  ✗ Secret is not valid JSON. Expected: {\"aws_access_key_id\": \"...\", \"aws_secret_access_key\": \"...\"}")
        return None

    access_key = secret_data.get('aws_access_key_id', '').strip()
    secret_key = secret_data.get('aws_secret_access_key', '').strip()

    if not access_key or not secret_key:
        print("  ✗ Secret missing required fields: 'aws_access_key_id' and/or 'aws_secret_access_key'")
        return None

    # Inject credentials into a new env copy
    secure_env = env.copy()
    secure_env['AWS_ACCESS_KEY_ID'] = access_key
    secure_env['AWS_SECRET_ACCESS_KEY'] = secret_key
    secure_env.pop('AWS_SESSION_TOKEN', None)
    secure_env.pop('AWS_PROFILE', None)

    print(f"  ✓ Credentials retrieved from Secrets Manager")
    return secure_env


def authenticate_account(account, env):
    """Authenticate an account by retrieving credentials from AWS Secrets Manager.

    Uses the configured 'profile' to access Secrets Manager, then uses
    the retrieved credentials for all downstream operations.

    Returns (success: bool, env: dict) where env has the retrieved credentials.
    """
    secure_env = authenticate_from_secrets_manager(account, env)
    if secure_env is None:
        return False, env

    # Verify the retrieved credentials work
    verify_cmd = ['aws', 'sts', 'get-caller-identity', '--output', 'text']
    verify_result = run_cmd(verify_cmd, secure_env)
    if verify_result.returncode == 0 and verify_result.stdout.strip():
        print(f"  ✓ Verified identity: {verify_result.stdout.strip()}")
        return True, secure_env

    print("  ✗ Retrieved credentials verification failed")
    return False, env


def get_all_enabled_regions(profile, env):
    """Return all enabled/available AWS regions for the profile account."""
    cmd = [
        'aws', 'ec2', 'describe-regions', '--all-regions', '--region', 'us-east-1',
        '--query', "Regions[?OptInStatus=='opt-in-not-required'||OptInStatus=='opted-in'].RegionName",
        '--output', 'text'
    ]
    if profile:
        cmd.extend(['--profile', profile])
    result = run_cmd(cmd, env)
    if result.returncode != 0:
        print(f"✗ Failed to discover regions for profile '{profile}'")
        print((result.stderr or result.stdout or '').strip())
        return []

    regions = [r.strip() for r in result.stdout.split() if r.strip()]
    print(f"✓ Profile '{profile}' regions discovered: {len(regions)}")
    return regions


def resolve_tag_filters_to_ids(tag_filters, profile, region, env):
    """Use AWS Resource Groups Tagging API to resolve tag filters to resource IDs.

    Terraformer --filter does not support tag-based filtering.
    This function discovers resource IDs that match the given tags,
    then returns properly typed ID-based filters that Terraformer understands.

    Terraformer filter rules:
      - Multiple --filter flags with the same Name are AND'd (intersection).
      - Colon-separated values within a single filter are OR'd (union).
      - Type= prefix scopes the filter to a specific Terraformer resource type.
    So we must group IDs by Terraformer type and join them with colons.
    """
    if not tag_filters:
        return []

    # Build tag-filter arguments for get-resources
    tag_filter_args = []
    for key, value in tag_filters.items():
        key = str(key).strip()
        value = str(value).strip()
        if key and value:
            tag_filter_args.append(f"Key={key},Values={value}")

    if not tag_filter_args:
        return []

    cmd = [
        'aws', 'resourcegroupstaggingapi', 'get-resources',
        '--region', region,
        '--output', 'json'
    ]
    if profile:
        cmd.extend(['--profile', profile])
    for tag_filter in tag_filter_args:
        cmd.extend(['--tag-filters', tag_filter])

    result = run_cmd(cmd, env)
    if result.returncode != 0:
        print(f"  ⚠ Tag lookup failed for region '{region}': {(result.stderr or '').strip()}")
        return []

    try:
        data = json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        print(f"  ⚠ Could not parse tag lookup response for region '{region}'")
        return []

    resources = data.get('ResourceTagMappingList', [])
    if not resources:
        print(f"  ⚠ No resources found matching tags in region '{region}'")
        return []

    # ARN-to-Terraformer type mapping
    # ARN format: arn:aws:<service>:<region>:<account>:<resource-type>/<id>
    # Terraformer uses its own type names for --filter Type= prefix
    arn_type_map = {
        ('ec2', 'vpc'): 'vpc',
        ('ec2', 'subnet'): 'subnet',
        ('ec2', 'security-group'): 'sg',
        ('ec2', 'route-table'): 'route_table',
        ('ec2', 'internet-gateway'): 'igw',
        ('ec2', 'nat-gateway'): 'nat',
        ('ec2', 'network-acl'): 'nacl',
        ('ec2', 'instance'): 'ec2_instance',
        ('ec2', 'elastic-ip'): 'eip',
        ('ec2', 'volume'): 'ebs',
        ('ec2', 'network-interface'): 'eni',
        ('elasticloadbalancing', 'loadbalancer'): 'alb',
        ('elasticloadbalancing', 'targetgroup'): 'alb',
        ('rds', 'db'): 'rds',
        ('rds', 'cluster'): 'rds',
        ('s3', None): 's3',
        ('lambda', 'function'): 'lambda_function',
        ('dynamodb', 'table'): 'dynamodb',
        ('sqs', None): 'sqs',
        ('sns', None): 'sns',
        ('iam', 'role'): 'iam',
        ('iam', 'policy'): 'iam',
        ('iam', 'user'): 'iam',
        ('logs', 'log-group'): 'cloudwatch',
        ('elasticache', 'cluster'): 'elasticache',
    }

    # Group resource IDs by Terraformer type
    type_ids = {}
    skipped_arns = []
    for item in resources:
        arn = item.get('ResourceARN', '')
        parts = arn.split(':')
        if len(parts) < 6:
            skipped_arns.append(arn)
            continue

        service = parts[2]
        resource_part = ':'.join(parts[5:])  # everything after account-id

        # Extract resource type and ID from the resource part
        # Formats: "type/id", "type:id", or just "id" (e.g. S3 bucket name)
        if '/' in resource_part:
            arn_resource_type, resource_id = resource_part.split('/', 1)
            # Handle nested paths like "function:name" or "loadbalancer/app/name/id"
            if '/' in resource_id:
                # For ALB/NLB: loadbalancer/app/<name>/<id> — use the full path
                resource_id = resource_id  # keep full sub-path for complex resources
        elif ':' in resource_part:
            arn_resource_type, resource_id = resource_part.split(':', 1)
        else:
            arn_resource_type = None
            resource_id = resource_part

        if not resource_id:
            skipped_arns.append(arn)
            continue

        # Look up Terraformer type
        tf_type = arn_type_map.get((service, arn_resource_type))
        if not tf_type:
            # Try service-only match (e.g., S3 bucket)
            tf_type = arn_type_map.get((service, None))
        if not tf_type:
            skipped_arns.append(arn)
            continue

        type_ids.setdefault(tf_type, set()).add(resource_id)

    if skipped_arns:
        print(f"  ℹ Skipped {len(skipped_arns)} resource(s) with no Terraformer type mapping:")
        for arn in skipped_arns:
            print(f"    {arn}")

    # Build one filter per Terraformer type with colon-separated IDs (OR within type)
    filters = []
    for tf_type, ids in sorted(type_ids.items()):
        joined = ':'.join(sorted(ids))
        filters.append(f"Type={tf_type};Name=id;Value={joined}")

    if filters:
        print(f"  ✓ Tag lookup found {len(resources)} resource(s) → {len(filters)} typed filter(s) in region '{region}'")
    return filters


def build_app_filters(app_config):
    """Build Terraformer --filter values from app config.

    Note: tag_filters are NOT converted here because they require
    per-region AWS API calls. They are resolved in import_for_account_app.
    """
    filters = []

    for expression in app_config.get('filter_expressions', []):
        expression = str(expression).strip()
        if expression:
            filters.append(expression)

    for vpc_id in app_config.get('vpc_ids', []):
        vpc_id = str(vpc_id).strip()
        if not vpc_id:
            continue
        filters.append(f"Type=vpc;Name=id;Value={vpc_id}")
        filters.append(f"Name=vpc-id;Value={vpc_id}")

    # tag_filters are resolved per-region in import_for_account_app
    # via resolve_tag_filters_to_ids() using AWS Resource Groups Tagging API

    return filters


def build_output_path(output_dir, account_name, app_name, region=None):
    """Return Terraformer path-pattern for account/app/(optional) region output."""
    account_segment = sanitize_name(account_name)
    app_segment = sanitize_name(app_name)
    parts = [output_dir, account_segment, app_segment]
    if region:
        parts.append(sanitize_name(region))
    base = os.path.join(*parts).replace('\\', '/')
    return f"{base}/"


def _write_temp_credentials_profile(env):
    """Write AWS credentials from env vars into a temp credentials file.

    Terraformer (Go AWS SDK) doesn't reliably pick up env vars when a local
    ~/.aws/config exists. Writing a named profile to a temp file and pointing
    AWS_SHARED_CREDENTIALS_FILE at it ensures Terraformer uses the right creds.

    Returns (profile_name, updated_env) where env has AWS_SHARED_CREDENTIALS_FILE set.
    """
    profile_name = 'terraformer-temp'
    access_key = env.get('AWS_ACCESS_KEY_ID', '')
    secret_key = env.get('AWS_SECRET_ACCESS_KEY', '')
    session_token = env.get('AWS_SESSION_TOKEN', '')

    if not all([access_key, secret_key]):
        return None, env

    # Write credentials to a temp file
    temp_creds_dir = os.path.join(os.environ.get('USERPROFILE', os.path.expanduser('~')), '.aws')
    os.makedirs(temp_creds_dir, exist_ok=True)
    temp_creds_file = os.path.join(temp_creds_dir, 'credentials_terraformer_temp')

    lines = [f'[{profile_name}]\n',
             f'aws_access_key_id = {access_key}\n',
             f'aws_secret_access_key = {secret_key}\n']
    if session_token:
        lines.append(f'aws_session_token = {session_token}\n')

    with open(temp_creds_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    # Point the SDK at this file
    updated_env = env.copy()
    updated_env['AWS_SHARED_CREDENTIALS_FILE'] = temp_creds_file
    updated_env.pop('AWS_PROFILE', None)
    updated_env.pop('AWS_DEFAULT_PROFILE', None)

    return profile_name, updated_env


def import_for_account_app(account, app_config, env, output_dir):
    """Run Terraformer import for one account and one app across regions."""
    account_name = account['name']

    # Write credentials to a temp profile that Terraformer can reliably read
    temp_profile, env = _write_temp_credentials_profile(env)
    profile = temp_profile or ''

    regions = account.get('regions', [])
    if not regions:
        regions = get_all_enabled_regions(profile, env)

    if not regions:
        print(f"✗ No regions available for account '{account_name}'")
        return 0, 0

    app_name = app_config['name']
    resources = app_config.get('resources', '*')
    tag_filters = app_config.get('tag_filters', {})
    filters = build_app_filters(app_config)
    base_path_pattern = build_output_path(output_dir, account_name, app_name)

    print(f"\n=== Account: {account_name} | App: {app_name} ===")
    print(f"Resources: {resources}")
    print(f"Regions: {', '.join(regions)}")
    print(f"Output base path: {base_path_pattern}")
    if tag_filters:
        print(f"Tag filters: {tag_filters}")
        print("  (will be resolved to resource IDs per region via AWS Tagging API)")
    if filters:
        print(f"Static filters ({len(filters)}):")
        for f in filters:
            print(f"  --filter={f}")
    if not filters and not tag_filters:
        print("Filters: none (importing all resources)")

    success_count = 0
    fail_count = 0

    for region in regions:
        region_path_pattern = build_output_path(output_dir, account_name, app_name, region=region)
        print(f"\nImporting account='{account_name}', app='{app_name}', region='{region}'")

        # Resolve tag filters to resource ID filters for this region
        region_filters = list(filters)  # copy static filters
        region_resources = resources    # default resource scope
        if tag_filters:
            tag_id_filters = resolve_tag_filters_to_ids(tag_filters, profile, region, env)
            if not tag_id_filters:
                print(f"  ⏩ Skipping region '{region}' — no resources match the specified tags")
                continue
            region_filters.extend(tag_id_filters)

            # Restrict --resources to only the types found in the tag lookup.
            # Without this, Terraformer imports ALL resource types that don't
            # have a Type= filter — defeating the purpose of tag filtering.
            tag_types = set()
            for f in tag_id_filters:
                for part in f.split(';'):
                    if part.startswith('Type='):
                        tag_types.add(part.split('=', 1)[1])
            if tag_types:
                region_resources = ','.join(sorted(tag_types))
                print(f"  Scoped --resources to tagged types: {region_resources}")

        if region_filters:
            print(f"  Resolved filters ({len(region_filters)}):")
            for f in region_filters:
                print(f"    --filter={f}")

        cmd = [
            'terraformer', 'import', 'aws',
            f'--resources={region_resources}',
            f'--regions={region}',
            f'--path-pattern={region_path_pattern}'
        ]
        # Pass --profile so Terraformer reads the temp credentials file
        if profile:
            cmd.insert(3, f'--profile={profile}')
        for item in region_filters:
            cmd.append(f'--filter={item}')

        result = run_cmd(cmd, env)
        if result.returncode == 0:
            print(f"✓ Import success for {region}")
            if result.stdout.strip():
                print(result.stdout.strip())
            success_count += 1
        else:
            print(f"✗ Import failed for {region}")
            error_output = (result.stderr or result.stdout or 'No error output returned by terraformer').strip()
            print(error_output)
            fail_count += 1

    return success_count, fail_count


def extract_aws_resources(accounts, apps, output_dir='terraform'):
    """Extract AWS resources for multiple accounts and app definitions."""
    env = build_terraformer_env()

    # ── Set up run logger ────────────────────────────────────────────────────
    timestamp = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    log_dir = os.path.join(output_dir, 'Logs')
    log_path = os.path.join(log_dir, f'import_run_{timestamp}.log')
    logger = RunLogger(log_path)

    try:
        return _run_extraction(accounts, apps, output_dir, env)
    finally:
        logger.close()


def _run_extraction(accounts, apps, output_dir, env):
    """Inner extraction logic (runs inside the logger context)."""
    if not check_terraformer_installed(env):
        print("Please install Terraformer: https://github.com/GoogleCloudPlatform/terraformer")
        return False

    if not check_aws_cli_installed(env):
        print("Please install AWS CLI and ensure it is available on PATH")
        return False

    if not check_aws_provider_supported(env):
        return False

    if not ensure_aws_provider_plugin(env):
        return False

    os.makedirs(output_dir, exist_ok=True)

    total_success = 0
    total_fail = 0
    processed_pairs = 0

    for account in accounts:
        account_name = account.get('name')
        profile = account.get('profile')
        secret_name = account.get('secret_name')
        if not account_name or not profile or not secret_name:
            print("✗ Invalid account config. Each account requires 'name', 'profile', and 'secret_name'.")
            total_fail += 1
            continue

        # Authenticate by retrieving credentials from Secrets Manager
        auth_success, account_env = authenticate_account(account, env)
        if not auth_success:
            total_fail += 1
            continue

        for app_config in apps:
            app_name = app_config.get('name')
            if not app_name:
                print("✗ Invalid app config. Each app requires 'name'.")
                total_fail += 1
                continue

            success_count, fail_count = import_for_account_app(account, app_config, account_env, output_dir)
            total_success += success_count
            total_fail += fail_count
            processed_pairs += 1

    generated_files = []
    for root, _, files in os.walk(output_dir):
        for file_name in files:
            generated_files.append(os.path.join(root, file_name))

    print("\n=== Summary ===")
    print(f"Processed account/app combinations: {processed_pairs}")
    print(f"Successful region imports: {total_success}")
    print(f"Failed region imports: {total_fail}")
    print(f"Output directory: {os.path.abspath(output_dir)}")
    print(f"Generated file count: {len(generated_files)}")

    return total_success > 0


if __name__ == '__main__':
    # Authentication: Retrieves AWS access keys from Secrets Manager.
    #
    # How it works:
    #   1. Uses the 'profile' (from ~/.aws/credentials) to access Secrets Manager
    #   2. Retrieves the secret specified by 'secret_name'
    #   3. Parses JSON: {"aws_access_key_id": "...", "aws_secret_access_key": "..."}
    #   4. Uses those credentials for all Terraformer import operations
    #
    # The profile only needs: secretsmanager:GetSecretValue permission
    # The secret's credentials need: ReadOnlyAccess (or whatever Terraformer needs)
    #
    # Account config fields:
    #   name           — display name for this account
    #   profile        — AWS CLI profile with Secrets Manager access
    #   secret_name    — Secrets Manager secret name or ARN
    #   secret_region  — (optional) region where the secret lives (default: us-east-1)
    #   regions        — list of regions to import from (empty = auto-discover)
    #
    ACCOUNTS = [
        {
            'name': 'account-default', # replace with your account display name
            'profile': 'default', # replace with your AWS CLI profile name that has access to the secret
            'secret_name': 'terraformer-import-credentials', # replace with your secret manager name or create a new AWS secret manager with this name
            'secret_region': 'eu-north-1', # replace with your secret region if not us-east-1
            'regions': ['ap-south-1', 'eu-north-1'] # Replace with your desired regions where you want to discover the resources.
        }
    ]

    # Multiple apps. Use resources='*' for all supported resources.
    # Filters are optional and combined per app.
    APPS = [
        {
            'name': 'Demotest', # replace with your app name
            'tag_filters': {
                'awsApplication': '<<arn for application>>' # replace with your tag filter
            }
        }
    ]

    OUTPUT_DIR = r"C:\Users\" # replace with your desired output path
    extract_aws_resources(ACCOUNTS, APPS, OUTPUT_DIR)