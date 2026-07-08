# AI Tooling

Brief notes on how team members used AI-assisted development tools on FraudPulse.

## Macharia Kibandi

Macharia used Claude (Anthropic) throughout backend development of FraudPulse. The AI assistant was used to design and implement the alerts and cases domain — including models, schemas, services, and REST endpoints — and to maintain consistency across the stack as the schema evolved. Claude also wrote and updated the test suite as the codebase changed, assisted with frontend integration by updating Angular services and components to match the backend API.

All output was reviewed before use. Design decisions were made by Macharia with Claude providing analysis of the options and their trade-offs.

## Victor Asena

I used a mix of AI tools throughout my work on FraudPulse — **OpenAI Codex**, **GitHub Copilot**, **Claude Code**, and **Claude (web)** — across the frontend, authentication, deployment, and backend integration.

My work spanned scaffolding the Angular frontend (Tailwind UI and mock workflows) and its responsive layouts, wiring Supabase authentication (login, route guard, and JWT verification), and building out the CI/CD and OCI deployment pipeline — GHCR image builds, SSH-based deploys, and the Nginx/Docker runtime configuration. On the backend I wired the `POST /transactions` flow end to end and aligned the DB schema, added the overview aggregation endpoint, and implemented the access-request approval flow alongside the public demo dashboard.

I used Copilot and Codex mainly for in-editor completions and quick edits, and Claude Code and Claude web for larger changes, debugging deployment issues, and thinking through design trade-offs. All output was reviewed before it was committed, and the design decisions were mine, with the tools providing suggestions and analysis of the options.

## Olalekan Erinoso

I used OpenAI (ChatGPT and Codex) as support tool during my work on the ML/model training and deployment parts of the FraudPulse project. For the ML work, I used Codex in writing and understanding scripts for Random Forest, LightGBM, calibrated LightGBM, inference testing, feature schema generation, threshold generation, and hyperparameter tuning.
I used ChatGPT to interpret model evaluation results such as confusion matrices, precision, recall, F1-score, ROC-AUC, PR-AUC, feature importance, and decision threshold outputs.

For deployment, I also used ChatGPT as a troubleshooting guide while setting up the backend environment on an Oracle Cloud Infrastructure VM. This included support with SSH access, environment variables, Nginx reverse proxy configuration, Let’s Encrypt SSL certificate setup, firewall/security rule debugging, and CORS configuration for frontend-backend communication.

All project work, commands, code execution, testing, deployment steps, and final decisions were carried out by me. AI was used to explain concepts, suggest commands, debug errors, and help structure drafted documentation, but I reviewed and applied the work myself within the project context.

## James Kilonzo

I used the **Cursor AI agent** to speed up day-to-day development across frontend and integration work, including the AI support assistant, UI updates, and project documentation. The agent helped me draft UI components, refine implementations, and iterate on fixes after code review while keeping changes aligned with existing project conventions.

For documentation, I prepared drafts with the required links and context, then used Cursor to accelerate writing the markdown files. I reviewed each document afterward to correct factual errors, broken links, and inconsistencies before committing.
