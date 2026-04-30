# Sources Catalog

> Master list of trusted sources for Phase 2's discovery sweep. Curated; updated as the ecosystem evolves. The `tech-scout-scanner` subagent reads this when prioritizing where to look.

## Tier 1 — Primary, sweep every week

These are signal-rich, low-noise, and almost always have something worth surfacing.

| Source | URL | Why |
|--------|-----|-----|
| Anthropic engineering blog | https://www.anthropic.com/engineering | Primary deep dives on Claude capabilities, agent design, prompt patterns |
| OpenAI research blog | https://openai.com/research | Benchmarks, capability research, model release context |
| Google DeepMind blog | https://deepmind.google/discover/blog/ | Foundational research, especially in agentic systems |
| Hugging Face Daily Papers | https://huggingface.co/papers | Curated, ranked daily papers — high signal |
| arXiv cs.AI recent | https://arxiv.org/list/cs.AI/recent | Raw research firehose, filter by abstract |
| arXiv cs.CL recent | https://arxiv.org/list/cs.CL/recent | NLP-side research |
| arXiv cs.LG recent | https://arxiv.org/list/cs.LG/recent | Machine learning side |
| Latent Space | https://latent.space | Swyx's analysis — practitioner perspective |
| Simon Willison's weblog | https://simonwillison.net | Tool releases, deep dives, reproducible experiments |
| a16z News | https://a16z.com/news | VC-perspective on what's getting funded and why |
| LangChain blog | https://blog.langchain.dev | Framework-side updates, integration patterns |
| LangGraph release notes | https://github.com/langchain-ai/langgraph/releases | Concrete API changes |
| Anthropic newsroom | https://www.anthropic.com/news | Product/policy announcements |

## Tier 2 — Secondary, sweep when relevant

Worth checking for specific topics or when Tier 1 is quiet.

| Source | URL | When to check |
|--------|-----|---------------|
| Hacker News front page | https://news.ycombinator.com | When validating buzz / finding contrarians |
| GitHub Trending Python | https://github.com/trending/python?since=weekly | New libraries gaining traction |
| GitHub Trending TypeScript | https://github.com/trending/typescript?since=weekly | Frontend-side AI tools |
| Sequoia Capital blog | https://www.sequoiacap.com/article-collection | VC analysis — slower cadence |
| Lightspeed blog | https://lsvp.com/insights/ | Same |
| Index Ventures blog | https://www.indexventures.com/perspectives/ | Same |
| Product Hunt — AI | https://www.producthunt.com/topics/artificial-intelligence | Newly launched AI products |
| Reddit r/MachineLearning | https://reddit.com/r/MachineLearning | Discussion + critique of papers |
| Reddit r/LocalLLaMA | https://reddit.com/r/LocalLLaMA | On-device / open-source angle |
| LlamaIndex blog | https://www.llamaindex.ai/blog | Framework updates |

## Tier 3 — Newsletters & podcasts

Useful for "what should I know this week" framing — read the latest issue per week.

- **Nate Jones** (Substack) — product manager perspective on AI failures and successes
- **Ben's Bites** (Substack) — daily AI news roundup
- **The Rundown AI** (Substack) — broader AI news
- **AI Research Roundup** (Substack) — paper summaries
- **Latent Space podcast** (latent.space) — long-form practitioner interviews
- **AI Engineer podcast** (YouTube) — practitioner talks
- **TwoMinutePapers** (YouTube) — accessible paper visualizations
- **Yannic Kilcher** (YouTube) — paper deep dives with critique

## Tier 4 — Twitter / X handles

If accessible. Use sparingly — high noise.

- @karpathy — Andrej Karpathy
- @swyx — Shawn Wang
- @hwchase17 — Harrison Chase (LangChain)
- @lateinteraction — Omar Khattab
- @jxnlco — Jason Liu
- @drjwrae — Jacob Andreas
- @nateliason — Nathan Liason
- @sama — Sam Altman
- @DrJimFan — Jim Fan
- @simonw — Simon Willison

## Tier 5 — Domain-specific (only if company hint matches)

| Domain | Sources |
|--------|---------|
| Hiring / Recruitment AI | HireEZ blog, Gem blog, Findem blog, Workday Talent Marketplace updates, LinkedIn Talent blog, AI in HR newsletters |
| Voice AI | Cartesia, Deepgram, ElevenLabs, Resemble blogs |
| Code AI | Cursor, Windsurf, GitHub Copilot blogs, Anthropic Claude Code updates |
| Agents / RAG | Same as Tier 1 + LlamaHub + Cohere blog |
| Security / Privacy AI | Wiz, Snyk blogs |

The scanner subagent should pull from this list **only if** the
`company_summary` indicates that domain is the focus. The first row is
an example of a domain entry; new domains can be added without code
changes.

## Categories Coverage Matrix

When Phase 2 finishes, ensure findings span at least 6 of these 15
categories. If a category is empty, **don't fabricate** — just note it.

| # | Category | Tier 1 source signals |
|---|----------|------------------------|
| 1 | Foundation Models | Anthropic, OpenAI, DeepMind, HF Daily Papers |
| 2 | Agent Frameworks | LangChain blog, LangGraph releases, GitHub Trending |
| 3 | Memory & State | arXiv (memory keyword), HF papers |
| 4 | Tools & Integration | Anthropic engineering, MCP-related repos |
| 5 | Compute & Sandboxing | HN, Product Hunt, GitHub Trending |
| 6 | Evaluation | Anthropic engineering, Latent Space |
| 7 | RAG / Retrieval | LlamaIndex, LangChain, arXiv |
| 8 | Voice / Multimodal | Cartesia/Deepgram blogs, HF |
| 9 | Inference / Serving | GitHub Trending, HN |
| 10 | Open Source Models | Reddit r/LocalLLaMA, HF |
| 11 | Research Papers | arXiv cs.AI/CL/LG, HF Daily Papers |
| 12 | Protocols / Standards | Anthropic, agent identity proposals |
| 13 | Infrastructure | a16z, Sequoia, HN |
| 14 | Developer Tools | Cursor/Windsurf/Claude Code blogs |
| 15 | Domain-specific | Tier 5 list above |

## Maintenance

When a source goes quiet for 2+ months or a new high-signal source
emerges, edit this file. The scanner reads it on every run. No code
changes needed.
