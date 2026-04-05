import type { APIDataType } from "@/types/api";
import { SIDEBAR_BUNDLES } from "@/utils/styleUtils";

// All bundle category names that exist in upstream Langflow.
// Categories in this list but NOT in SIDEBAR_BUNDLES are hidden from search.
const ALL_BUNDLE_NAMES = new Set([
  "aiml", "agentics", "agentql", "altk", "languagemodels", "embeddings",
  "memories", "amazon", "anthropic", "apify", "arxiv", "assemblyai",
  "azure", "baidu", "bing", "cassandra", "chroma", "clickhouse",
  "cleanlab", "cloudflare", "cohere", "cometapi", "composio",
  "confluence", "couchbase", "crewai", "cuga", "datastax", "deepseek",
  "docling", "duckduckgo", "elastic", "exa", "FAISS", "firecrawl",
  "git", "glean", "gmail", "google", "groq", "homeassistant",
  "huggingface", "ibm", "icosacomputing", "jigsawstack",
  "langchain_utilities", "langwatch", "litellm", "lmstudio", "maritalk",
  "mem0", "milvus", "mistral", "mongodb", "needle", "notdiamond",
  "Notion", "novita", "nvidia", "olivya", "ollama", "openai",
  "openrouter", "perplexity", "pgvector", "pinecone", "qdrant", "redis",
  "sambanova", "scrapegraph", "searchapi", "serpapi", "serper",
  "supabase", "tavily", "twelvelabs", "unstructured", "upstash",
  "vlmrun", "vectara", "vectorstores", "vllm", "weaviate", "vertexai",
  "wikipedia", "wolframalpha", "xai", "yahoosearch", "youtube",
]);

const ALLOWED_BUNDLE_NAMES = new Set(SIDEBAR_BUNDLES.map((b) => b.name));

export const applyBundleFilter = (filteredData: APIDataType): APIDataType => {
  return Object.fromEntries(
    Object.entries(filteredData).filter(
      ([categoryName]) =>
        // Keep if: not a bundle at all, OR an allowed bundle
        !ALL_BUNDLE_NAMES.has(categoryName) ||
        ALLOWED_BUNDLE_NAMES.has(categoryName),
    ),
  ) as APIDataType;
};
