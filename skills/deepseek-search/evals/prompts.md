# Evaluation Prompts: DeepSeek Search

This test suite defines evaluation scenarios for `deepseek-search` covering the primary workflows:

1. Basic web search with result parsing and citation
2. Search with query operators (site:, lang:, after:/before:, exclusions)
3. Full-page content retrieval via need_content and Fetch API
4. Error handling and retry behavior

---

## Prompt 1: Basic Search and Citation

- **ID**: 1
- **Short Name**: `basic-search-cite`
- **Workflow Step**: Search for a topic and cite sources properly

### User Prompt

> Search for "DeepSeek V4 release" and give me a summary with citations. I want to know the key features, release date, and where to find the model. Cite each claim with the source domain in markdown link format like [github.com](url).

### Acceptance Assertions

1. `search tool is invoked with query "DeepSeek V4 release"` (Objective: tool call captured with correct query)
2. `At least 3 results returned` (Objective: results array length ≥ 3)
3. `Response cites sources using [domain](url) markdown format` (Objective: pattern match for bracketed domain + URL)
4. `Summary includes key features, release date, and model availability` (Objective: human review of content coverage)
5. `Results sorted or filtered by rerank_score/authority` (Objective: evidence of relevance-aware selection)

---

## Prompt 2: Search with Query Operators

- **ID**: 2
- **Short Name**: `operator-search`
- **Workflow Step**: Apply query operators for targeted results

### User Prompt

> Find recent information about DeepSeek only from GitHub or HuggingFace, in English, published after January 2025. Exclude any advertising or marketing pages. Show me the top 5 results with their relevance scores.

### Acceptance Assertions

1. `search query includes site:github.com OR site:huggingface.co` (Objective: tool call query contains operator)
2. `search query includes lang:en` (Objective: tool call query contains operator)
3. `search query includes after:2025-01-01` (Objective: tool call query contains operator)
4. `search query includes -advertisement -marketing` (Objective: tool call query contains exclusion operators)
5. `count parameter set to 5` (Objective: tool call payload count=5)
6. `Results show rerank_score and authority fields` (Objective: response parsing includes these fields)

---

## Prompt 3: Full-Page Content Retrieval

- **ID**: 3
- **Short Name**: `full-content-fetch`
- **Workflow Step**: Retrieve full page content via need_content and Fetch API

### User Prompt

> Search for "DeepSeek API pricing" and get the full content of the most authoritative result (authority ≥ 3). Then also fetch the DeepSeek API docs pricing page directly to compare.

### Acceptance Assertions

1. `First search uses need_content=true` (Objective: tool call payload need_content=true)
2. `Result with highest authority ≥ 3 is identified` (Objective: logic selects by authority field)
3. `Fetch API called on the selected result's URL` (Objective: second tool call to fetch with correct URL)
4. `Fetch API called on https://api-docs.deepseek.com/quick_start/pricing` (Objective: direct fetch of known URL)
5. `Both responses contain Markdown content in content field` (Objective: content field non-empty, Markdown format)
6. `Comparison highlights differences/similarities` (Objective: human review of synthesis)

---

## Prompt 4: Error Handling and Retry

- **ID**: 4
- **Short Name**: `error-handling`
- **Workflow Step**: Graceful handling of API errors

### User Prompt

> Try to search with an invalid count parameter (100) and show me how the skill handles the error. Then do a valid search to confirm it still works.

### Acceptance Assertions

1. `First search attempt with count=100 triggers 400 error` (Objective: tool call made, error caught)
2. `Error message surfaced to user with actionable guidance` (Objective: response explains the error and fix)
3. `Second search with valid count=10 succeeds` (Objective: subsequent tool call works)
4. `No crash or unhandled exception` (Objective: process exits cleanly)

---

## Prompt 5: Rate Limit Simulation

- **ID**: 5
- **Short Name**: `rate-limit-retry`
- **Workflow Step**: Automatic retry on 429/5xx

### User Prompt

> Search for "test query" — if you hit a rate limit or server error, retry automatically up to 3 times with backoff. Report whether it succeeded or failed after retries.

### Acceptance Assertions

1. `Retry logic implemented for 429, 500, 502, 503, 504, 408` (Objective: code inspection of retryable statuses)
2. `Exponential backoff with base 1.5s` (Objective: code inspection of backoff formula)
3. `Max 3 retries before giving up` (Objective: code inspection of MAX_RETRIES=3)
4. `Non-retryable errors (400, 401, 402, 403, 404) fail immediately` (Objective: code inspection of error classification)

---