"""
Discord Bot Service for BookFairy
Implements Discord slash commands and user interactions
Integrates with UserRequest, WorkflowExecution, and governance models
"""
import discord
from discord import app_commands
from typing import Optional, Dict, Any
import asyncio
import uuid
from datetime import datetime, timedelta
import os
import sys

# Add project root to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from services.shared.models.user_request import (
    UserRequest, RequestType, RequestSource, RequestPriority,
    UserRequestRegistry, UserSession, RequestStatus
)
from services.shared.models.workflow import (
    WorkflowExecution, WorkflowType, WorkflowStatus, WorkflowRegistry
)
from services.shared.models.governance import (
    AuditLensFramework, AuditLens, AuditSeverity, AuditFinding
)


class BookFairyBot(discord.Bot):
    """BookFairy Discord Bot with governance and audit integration"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Initialize registries (in production, these would be shared services)
        self.request_registry = UserRequestRegistry()
        self.workflow_registry = WorkflowRegistry()
        self.audit_framework = AuditLensFramework()

        # Configuration - in production load from config.py
        self.config = {
            "DISCORD_TOKEN": os.getenv("DISCORD_TOKEN", "your_token_here"),
            "MAX_CONCURRENT_WORKFLOWS": int(os.getenv("MAX_WORKFLOWS", "10")),
            "DEFAULT_TIMEOUT_SECONDS": 300,
            "RATE_LIMIT_REQUESTS_PER_MINUTE": 10,
            "GOVERNANCE_ENABLED": True
        }

        # Setup command tree
        self.tree = app_commands.CommandTree(self)

        # Track active workflows
        self.active_workflows = set()

        print("BookFairyBot initialized with governance framework")

    async def setup_hook(self):
        """Setup hook for bot initialization"""
        await self.tree.sync()
        print("Discord commands synchronized")

    async def on_ready(self):
        """Bot ready event"""
        print(f"BookFairy Bot ready! Logged in as {self.user}")
        print("Available commands: /search, /download, /recommend, /status, /help")

    async def on_interaction(self, interaction: discord.Interaction):
        """Handle all interactions with governance audit"""
        if not isinstance(interaction, discord.Interaction):
            return

        # Apply security audit lens for all interactions
        await self._apply_security_audit_for_interaction(interaction)

        await self.process_interactions.interaction(interaction)

    async def _apply_security_audit_for_interaction(self, interaction: discord.Interaction):
        """Apply security audit lens to Discord interactions"""
        try:
            # Create audit target data
            audit_target = {
                "interaction_type": interaction.type.name,
                "user_id": str(interaction.user.id),
                "channel_id": str(interaction.channel_id),
                "guild_id": str(interaction.guild_id) if interaction.guild_id else None,
                "command_name": interaction.command.name if interaction.command else None,
            }

            # Apply security audit lens
            findings = self.audit_framework.apply_lens(
                AuditLens.SAFETY_SECURITY,
                audit_target,
                {"context": "discord_interaction"}
            )

            # Log findings for security monitoring
            for finding in findings:
                if finding.severity in [AuditSeverity.BLOCKER, AuditSeverity.HIGH]:
                    print(f"🚨 SECURITY FINDING: {finding.title} - {finding.description}")

            # Check for critical security issues
            if any(f.severity == AuditSeverity.BLOCKER for f in findings):
                print("CRITICAL SECURITY ISSUE DETECTED - CONTACT ADMINISTRATOR")
                # In production, this would trigger security alerts

        except Exception as e:
            print(f"Security audit error: {e}")

    @app_commands.command(name="search", description="Search for audiobooks by title or author")
    @app_commands.describe(query="What to search for (book title, author, genre)")
    async def search_command(self, interaction: discord.Interaction, query: str):
        """Handle audiobook search command"""

        # Create UserRequest for governance tracking
        request = UserRequest(
            request_id="",
            user_id=str(interaction.user.id),
            request_type=RequestType.SEARCH,
            content=query,
            parameters={"query": query, "max_results": 10},
            source=RequestSource.DISCORD_SLASH_COMMAND,
            channel_id=str(interaction.channel_id),
            guild_id=str(interaction.guild_id),
            priority=RequestPriority.NORMAL
        )

        # Register and validate request
        if self._validate_request_can_proceed(request):

            # Store request
            self.request_registry.register_request(request)

            # Create search workflow
            workflow = self._create_search_workflow(request)
            self.workflow_registry.register_workflow(workflow)
            self.active_workflows.add(workflow.workflow_id)

            # Acknowledge interaction immediately
            await interaction.response.send_message(
                f"🔍 Searching for: **{query}**\n"
                f"Workflow ID: `{workflow.workflow_id[:8]}...`\n"
                f"Requested by: {interaction.user.mention}\n"
                f"⚡ Processing your request...",
                ephemeral=False
            )

            # Start workflow processing (in production, this would be queued)
            asyncio.create_task(self._process_search_workflow(workflow.workflow_id))

        else:
            await interaction.response.send_message(
                "❌ Request could not be processed due to rate limiting or governance restrictions.",
                ephemeral=True
            )

    @app_commands.command(name="status", description="Check status of your requests and workflows")
    async def status_command(self, interaction: discord.Interaction):
        """Show user request and workflow status"""

        user_id = str(interaction.user.id)
        user_requests = self.request_registry.get_user_requests(user_id)
        user_workflows = self.workflow_registry.get_user_workflows(user_id)

        status_embed = discord.Embed(
            title="📊 Your BookFairy Status",
            color=0x3498db,
            timestamp=datetime.utcnow()
        )

        # Recent Requests
        if user_requests:
            request_status = []
            for req in user_requests[-5:]:  # Last 5 requests
                status_emoji = {
                    "pending": "⏳",
                    "processing": "⚡",
                    "completed": "✅",
                    "failed": "❌"
                }.get(req.status, "❓")

                # Get discord embed data
                embed_data = req.get_discord_embed_data()
                request_status.append(f"{status_emoji} {req.request_type.value.title()} - {req.status}")

            status_embed.add_field(
                name="Recent Requests",
                value="\n".join(request_status) if request_status else "No recent requests",
                inline=False
            )
        else:
            status_embed.add_field(
                name="Recent Requests",
                value="No requests found",
                inline=False
            )

        # Active Workflows
        active_workflows = [w for w in user_workflows if w.status == WorkflowStatus.RUNNING]
        if active_workflows:
            workflow_status = []
            for workflow in active_workflows[:3]:  # Limit to 3
                progress = f"{workflow.progress_percentage:.0f}%"
                workflow_status.append(
                    f"🔄 {workflow.workflow_type.value}: {workflow.name[:30]}... ({progress})"
                )

            status_embed.add_field(
                name="Active Workflows",
                value="\n".join(workflow_status),
                inline=False
            )

        status_embed.set_footer(text=f"User ID: {user_id}")

        await interaction.response.send_message(embed=status_embed, ephemeral=True)

    @app_commands.command(name="help", description="Get help with BookFairy commands")
    async def help_command(self, interaction: discord.Interaction):
        """Show help information"""

        help_embed = discord.Embed(
            title="📚 BookFairy Bot - Help",
            description="Your audiobook management companion with governance",
            color=0x9b59b6,
            timestamp=datetime.utcnow()
        )

        help_embed.add_field(
            name="🔍 /search [query]",
            value="Search for audiobooks by title, author, or genre",
            inline=False
        )

        help_embed.add_field(
            name="📊 /status",
            value="Check the status of your requests and workflows",
            inline=False
        )

        help_embed.add_field(
            name="📖 /download [book_id]",
            value="Download a specific audiobook (requires approval)",
            inline=False
        )

        help_embed.add_field(
            name="💡 /recommend",
            value="Get AI-powered audiobook recommendations",
            inline=False
        )

        help_embed.add_field(
            name="❓ /help",
            value="Show this help message",
            inline=False
        )

        help_embed.add_field(
            name="🔒 Governance Features",
            value="• All interactions are audited and monitored\n"
                  "• Rate limiting protects system stability\n"
                  "• Sensitive operations require approval",
            inline=False
        )

        await interaction.response.send_message(embed=help_embed, ephemeral=True)

    def _validate_request_can_proceed(self, request: UserRequest) -> bool:
        """Validate request using governance framework"""

        # Check rate limiting
        user_requests = self.request_registry.get_user_requests(request.user_id)

        if request.should_be_rate_limited(user_requests):
            print(f"Rate limit exceeded for user {request.user_id}")
            return False

        # Apply governance audit lens
        findings = self._apply_governance_audit(request)

        # Check for blocking findings
        blocking_findings = [f for f in findings if f.is_blocking()]
        if blocking_findings:
            print(f"Blocking governance findings for request {request.request_id}")
            return False

        # Check concurrent workflow limits
        if len(self.active_workflows) >= self.config["MAX_CONCURRENT_WORKFLOWS"]:
            print("Maximum concurrent workflows exceeded")
            return False

        return True

    def _apply_governance_audit(self, request: UserRequest) -> list[AuditFinding]:
        """Apply governance audit lenses to request"""
        findings = []

        # Apply performance lens for resource impact
        perf_findings = self.audit_framework.apply_lens(
            AuditLens.PERFORMANCE_EFFICIENCY,
            request,
            {"context": "user_request_processing"}
        )
        findings.extend(perf_findings)

        # Apply security lens for user interactions
        security_findings = self.audit_framework.apply_lens(
            AuditLens.SAFETY_SECURITY,
            request,
            {"context": "discord_user_request", "user_id": request.user_id}
        )
        findings.extend(security_findings)

        # Apply communication lens for user experience
        comm_findings = self.audit_framework.apply_lens(
            AuditLens.COMMUNICATION_CLARITY,
            request,
            {"context": "user_interface"}
        )
        findings.extend(comm_findings)

        return findings

    def _create_search_workflow(self, request: UserRequest) -> WorkflowExecution:
        """Create search workflow from user request"""

        from services.shared.models.workflow import WorkflowStep

        # Create workflow execution
        workflow = WorkflowExecution(
            workflow_id="",
            workflow_type=WorkflowType.SEARCH,
            user_id=request.user_id,
            name=f"Search: {request.content[:50]}",
            description=f"Search audiobook collection for '{request.content}'"
        )

        # Add search steps
        steps = [
            WorkflowStep(
                step_id="",
                name="Validate Search Query",
                description="Validate and sanitize search query",
                service_name="discord-bot",
                endpoint="/internal/search/validate",
                method="POST"
            ),
            WorkflowStep(
                step_id="",
                name="Execute Search",
                description="Search audiobook database",
                service_name="lazylibrarian",
                endpoint="/api/search",
                method="GET",
                depends_on=["validate"]
            ),
            WorkflowStep(
                step_id="",
                name="Format Results",
                description="Format search results for Discord",
                service_name="discord-bot",
                endpoint="/internal/search/format",
                method="POST",
                depends_on=["execute"]
            )
        ]

        # Set proper dependencies
        step_ids = {}
        workflow.steps = []

        for i, step in enumerate(steps):
            step.step_id = f"search_{i+1}"
            step_ids[step.step_id] = step
            workflow.steps.append(step)

        # Update dependency references
        for step in workflow.steps:
            step.depends_on = [dep_id for dep_id in step.depends_on if dep_id in step_ids]

        return workflow

    async def _process_search_workflow(self, workflow_id: str):
        """Process search workflow asynchronously"""

        # Get workflow
        workflow = self.workflow_registry.get_workflow(workflow_id)
        if not workflow:
            return

        try:
            # Mark as running
            workflow.start_workflow()

            # Simulate workflow processing (in production, this would call actual services)
            await asyncio.sleep(2)  # Simulate processing time

            # Mock search results
            mock_results = [
                {
                    "title": f"{workflow.input_parameters.get('query', 'Book')} - Chapter 1",
                    "author": "Test Author",
                    "id": f"mock_{uuid.uuid4().hex[:8]}"
                },
                {
                    "title": f"{workflow.input_parameters.get('query', 'Book')} - Chapter 2",
                    "author": "Test Author",
                    "id": f"mock_{uuid.uuid4().hex[:8]}"
                }
            ]

            # Complete workflow
            workflow.complete_workflow(mock_results)

            print(f"Workflow {workflow_id} completed successfully")

        except Exception as e:
            # Handle workflow failure
            workflow.fail_workflow(f"Search workflow failed: {str(e)}")
            print(f"Workflow {workflow_id} failed: {e}")


def main():
    """Main function to run the bot"""

    # Initialize bot
    intents = discord.Intents.default()
    intents.guilds = True
    intents.messages = True

    bot = BookFairyBot(intents=intents)

    # Get token from environment (in production, load from config)
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("ERROR: DISCORD_TOKEN environment variable not set")
        return

    try:
        print("Starting BookFairy Discord Bot...")
        bot.run(token)
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"Bot failed to start: {e}")
    finally:
        print("Bot shutdown complete")


if __name__ == "__main__":
    main()
