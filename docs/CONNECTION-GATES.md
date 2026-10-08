# Connection gates — pending external user approvals

- **GitHub**: a connected integration can update existing repositories but cannot create repositories. The repository exists but is public. Switch visibility to private if storing company-specific configurations.
- **Supabase**: only organization visible is `andreydecorvital-sudo's Org` (ID privado, consultável na conta Supabase), but creating a project requires explicit user selection of organization and confirmation of quoted cost. No new project or migration was applied.
- **Vercel**: an existing independent project `orquestra-dev` is online in `vitaldecor` (ID consultável na conta Vercel). Link it to the new private GitHub repository (root `web-live`) once created; the current online site is NOT the new v1.0. Until a dedicated Supabase project exists, a live login cannot work.
- **GPT and Claude**: user must log in to their CLIs in the runner environment; an assistant cannot transfer authentication sessions or create access tokens from the chat.
- **24/7**: Vercel hosting and database availability do not run LLM jobs themselves. A persistent authenticated worker/remote runner must remain alive. Choosing paid runtime resources requires cost consent.

Recommended first end-to-end integration: private Supabase → Vercel public config → project + device pairing → diagnose task → Codex task with locally saved patch → joint review. Never connect production Argoplace until the full isolated pilot passes.
