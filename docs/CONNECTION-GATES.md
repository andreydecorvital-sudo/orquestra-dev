# Connection gates — pending external user approvals

- **GitHub**: `andreydecorvital-sudo/orquestra-dev` is now populated (44 files) with a passing CI run, and is linked to Vercel. It is PUBLIC. Switch visibility to private before including company-specific details.
- **Supabase**: only organization visible is `andreydecorvital-sudo's Org` (ID privado, consultável na conta Supabase), but creating a project requires explicit user selection of organization and confirmation of quoted cost. No new project or migration was applied.
- **Vercel**: GitHub-linked project `orquestra-dev-app` (root `web-live`) is deployed to `https://orquestra-dev-app.vercel.app/` and returns HTTP 200. The previous `orquestra-dev.vercel.app` project remains untouched. No Supabase login can work until the dedicated database is provisioned.
- **GPT and Claude**: user must log in to their CLIs in the runner environment; an assistant cannot transfer authentication sessions or create access tokens from the chat.
- **24/7**: Vercel hosting and database availability do not run LLM jobs themselves. A persistent authenticated worker/remote runner must remain alive. Choosing paid runtime resources requires cost consent.

Recommended first end-to-end integration: private Supabase → Vercel public config → project + device pairing → diagnose task → Codex task with locally saved patch → joint review. Never connect production Argoplace until the full isolated pilot passes.
