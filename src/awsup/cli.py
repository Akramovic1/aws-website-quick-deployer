#!/usr/bin/env python3
"""
AWS Website Deployer CLI Entry Point
"""
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import click
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table

from .config import DeploymentConfig, AWSCredentialValidator
from .validators import DomainValidator, FileValidator, SecurityValidator
from .production_deployer import CompleteProductionDeployer

console = Console()

# Configure logging with rich
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console, rich_tracebacks=True)]
)
logger = logging.getLogger(__name__)


class ProductionDeployer:
    """Legacy wrapper for backward compatibility"""
    
    def __init__(self, config: DeploymentConfig):
        self.deployer = CompleteProductionDeployer(config)
    
    def preflight_checks(self) -> bool:
        """Run comprehensive preflight checks"""
        return self.deployer.preflight_checks()
    
    def deploy_phase1(self) -> Dict:
        """Deploy Phase 1: Route53 setup"""
        return self.deployer.deploy_phase1()
    
    def deploy_phase2(self, website_path: Optional[str] = None) -> Dict:
        """Deploy Phase 2: Full deployment"""
        return self.deployer.deploy_phase2(website_path)
    
    def show_deployment_status(self):
        """Display current deployment status"""
        return self.deployer.show_detailed_status()


@click.group()
@click.option('--config', '-c', help='Configuration file path')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx, config, verbose):
    """Production-grade AWS website deployment tool"""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    ctx.ensure_object(dict)
    ctx.obj['config_path'] = config


@cli.command()
@click.argument('domain')
@click.option('--region', default='us-east-1', help='AWS region')
@click.option('--environment', default='prod', help='Environment name')
@click.pass_context
def init(ctx, domain, region, environment):
    """Initialize deployment configuration"""
    try:
        # Validate domain
        is_valid, error = DomainValidator.validate_domain(domain)
        if not is_valid:
            console.print(f"[red]❌ {error}[/red]")
            sys.exit(1)
        
        # Create configuration
        config = DeploymentConfig(
            domain=DomainValidator.normalize_domain(domain),
            region=region,
            environment=environment
        )
        
        # Save configuration
        config_path = ctx.obj.get('config_path') or f'.aws-deploy-{domain}.json'
        config.to_file(config_path)
        
        console.print(f"[green]Configuration saved to {config_path}[/green]")
        console.print(f"[blue]Domain: {config.domain}[/blue]")
        console.print(f"[blue]Region: {config.region}[/blue]")
        console.print(f"[blue]Environment: {config.environment}[/blue]")
        
    except Exception as e:
        console.print(f"[red]Initialization failed: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('domain')
@click.pass_context
def phase1(ctx, domain):
    """Deploy Phase 1: Route53 setup"""
    try:
        config = _load_config(ctx, domain)
        deployer = ProductionDeployer(config)
        
        if not deployer.preflight_checks():
            sys.exit(1)
        
        deployer.deploy_phase1()
        
    except Exception as e:
        console.print(f"[red]❌ Phase 1 deployment failed: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('domain')
@click.option('--website-path', help='Path to website files')
@click.pass_context
def phase2(ctx, domain, website_path):
    """Deploy Phase 2: Full deployment"""
    try:
        config = _load_config(ctx, domain)
        deployer = ProductionDeployer(config)
        
        if not deployer.preflight_checks():
            sys.exit(1)
        
        # Validate website path if provided
        if website_path:
            is_valid, error = FileValidator.validate_website_path(website_path)
            if not is_valid:
                console.print(f"[red]❌ Website validation failed: {error}[/red]")
                sys.exit(1)
        
        deployer.deploy_phase2(website_path)
        
    except Exception as e:
        console.print(f"[red]❌ Phase 2 deployment failed: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('domain')
@click.option('--website-path', help='Path to website files')
@click.pass_context
def deploy(ctx, domain, website_path):
    """Deploy both phases (complete deployment)"""
    try:
        config = _load_config(ctx, domain)
        deployer = ProductionDeployer(config)
        
        if not deployer.preflight_checks():
            sys.exit(1)
        
        # Phase 1
        result = deployer.deploy_phase1()
        
        # Always ask about NS record configuration
        console.print("\n")
        response = click.confirm("Have you configured the NS records at your domain registrar?")
        if not response:
            console.print("[blue]Please configure the NS records shown above at your registrar, then run:[/blue]")
            console.print(f"[blue]   awsup phase2 {domain}[/blue]")
            if website_path:
                console.print(f"[blue]   --website-path {website_path}[/blue]")
            sys.exit(0)
        
        # Phase 2
        deployer.deploy_phase2(website_path)
        
    except Exception as e:
        console.print(f"[red]❌ Complete deployment failed: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('domain')
@click.pass_context
def status(ctx, domain):
    """Show deployment status"""
    try:
        config = _load_config(ctx, domain)
        deployer = ProductionDeployer(config)
        deployer.show_deployment_status()
        
    except Exception as e:
        console.print(f"[red]❌ Failed to get status: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('domain')
@click.option('--paths', help='Comma-separated paths to invalidate (default: /*)')
@click.pass_context
def invalidate(ctx, domain, paths):
    """Invalidate CloudFront cache"""
    try:
        config = _load_config(ctx, domain)
        deployer = ProductionDeployer(config)
        
        path_list = paths.split(',') if paths else None
        deployer.deployer.invalidate_cache(path_list)
        
    except Exception as e:
        console.print(f"[red]❌ Cache invalidation failed: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('domain')
@click.option('--phase', type=click.Choice(['1', '2', 'all']), default='all', help='Which phase to cleanup')
@click.confirmation_option(prompt='This will delete AWS resources. Continue?')
@click.pass_context
def cleanup(ctx, domain, phase):
    """Cleanup AWS resources"""
    try:
        config = _load_config(ctx, domain)
        deployer = ProductionDeployer(config)
        
        if phase == '1':
            deployer.deployer.cleanup_phase1()
        elif phase == '2':
            deployer.deployer.cleanup_phase2()
        else:  # all
            deployer.deployer.cleanup_all()
        
    except Exception as e:
        console.print(f"[red]❌ Cleanup failed: {e}[/red]")
        sys.exit(1)


def _load_config(ctx, domain: str) -> DeploymentConfig:
    """Load configuration from file or create default"""
    config_path = ctx.obj.get('config_path') or f'.aws-deploy-{domain}.json'
    
    try:
        if Path(config_path).exists():
            return DeploymentConfig.from_file(config_path)
        else:
            # Create default config
            return DeploymentConfig(domain=domain)
    except Exception as e:
        console.print(f"[red]❌ Failed to load configuration: {e}[/red]")
        sys.exit(1)


def main():
    """Main entry point for the CLI"""
    cli()


if __name__ == '__main__':
    main()