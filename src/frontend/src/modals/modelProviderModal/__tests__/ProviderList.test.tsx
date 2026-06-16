import { render, screen } from "@testing-library/react";
import ProviderList from "../components/ProviderList";

// Mock ForwardedIconComponent
jest.mock("@/components/common/genericIconComponent", () => ({
  __esModule: true,
  ForwardedIconComponent: ({
    name,
    className,
  }: {
    name: string;
    className?: string;
  }) => (
    <span data-testid={`icon-${name}`} className={className}>
      {name}
    </span>
  ),
}));

// Mock LoadingTextComponent
jest.mock("@/components/common/loadingTextComponent", () => ({
  __esModule: true,
  default: ({ text }: { text: string }) => (
    <span data-testid="loading-text">{text}</span>
  ),
}));

// Mock provider data — only ALLOWED_PROVIDERS (vllm, vllm embeddings, ollama)
const mockProviders = [
  {
    provider: "Ollama",
    icon: "Ollama",
    is_enabled: true,
    models: [
      { model_name: "llama3", metadata: { model_type: "llm" } },
      { model_name: "nomic-embed-text", metadata: { model_type: "embeddings" } },
    ],
  },
  {
    provider: "vLLM",
    icon: "vLLM",
    is_enabled: false,
    models: [],
  },
  {
    provider: "vLLM Embeddings",
    icon: "vLLM",
    is_enabled: false,
    models: [],
  },
];

let mockIsLoading = false;
let mockIsFetching = false;

jest.mock("@/controllers/API/queries/models/use-get-model-providers", () => ({
  useGetModelProviders: jest.fn(() => ({
    data: mockProviders,
    isLoading: mockIsLoading,
    isFetching: mockIsFetching,
  })),
}));

interface MockProviderListItemProps {
  provider: { provider: string; model_count?: number };
  isSelected: boolean;
  onSelect: (provider: MockProviderListItemProps["provider"]) => void;
}

// Mock ProviderListItem
jest.mock("../components/ProviderListItem", () => ({
  __esModule: true,
  default: ({ provider, isSelected, onSelect }: MockProviderListItemProps) => (
    <div
      data-testid={`provider-item-${provider.provider}`}
      data-selected={isSelected}
      onClick={() => onSelect(provider)}
    >
      {provider.provider} - {provider.model_count} models
    </div>
  ),
}));

describe("ProviderList", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockIsLoading = false;
    mockIsFetching = false;
  });

  describe("Loading State", () => {
    it("should show loading state when isLoading is true", () => {
      mockIsLoading = true;

      // Re-import to get fresh mock
      const useGetModelProvidersMock =
        require("@/controllers/API/queries/models/use-get-model-providers").useGetModelProviders;
      useGetModelProvidersMock.mockReturnValueOnce({
        data: [],
        isLoading: true,
        isFetching: false,
      });

      render(<ProviderList modelType="all" />);

      expect(screen.getByTestId("provider-list-loading")).toBeInTheDocument();
      expect(screen.getByText("Loading providers")).toBeInTheDocument();
    });
  });

  describe("Provider Display", () => {
    it("should render provider list container", () => {
      render(<ProviderList modelType="all" />);

      expect(screen.getByTestId("provider-list")).toBeInTheDocument();
    });

    it("should render all allowed providers with all model types", () => {
      render(<ProviderList modelType="all" />);

      expect(screen.getByTestId("provider-item-Ollama")).toBeInTheDocument();
      expect(screen.getByTestId("provider-item-vLLM")).toBeInTheDocument();
      expect(
        screen.getByTestId("provider-item-vLLM Embeddings"),
      ).toBeInTheDocument();
    });

    it("should filter LLM providers by model type", () => {
      render(<ProviderList modelType="llm" />);

      // All allowed providers appear (vLLM explicitly maps to llm type)
      expect(screen.getByTestId("provider-item-Ollama")).toBeInTheDocument();
      expect(screen.getByTestId("provider-item-vLLM")).toBeInTheDocument();
      // vLLM Embeddings still renders with 0 llm models
      expect(
        screen.getByTestId("provider-item-vLLM Embeddings"),
      ).toBeInTheDocument();
    });

    it("should filter embedding providers by model type", () => {
      render(<ProviderList modelType="embeddings" />);

      // All allowed providers appear (vLLM Embeddings explicitly maps to embeddings)
      expect(screen.getByTestId("provider-item-Ollama")).toBeInTheDocument();
      // vLLM still renders with 0 embedding models
      expect(screen.getByTestId("provider-item-vLLM")).toBeInTheDocument();
      expect(
        screen.getByTestId("provider-item-vLLM Embeddings"),
      ).toBeInTheDocument();
    });

    it("should exclude providers not in the allowed list", () => {
      const useGetModelProvidersMock =
        require("@/controllers/API/queries/models/use-get-model-providers").useGetModelProviders;
      useGetModelProvidersMock.mockReturnValueOnce({
        data: [
          ...mockProviders,
          { provider: "OpenAI", icon: "Bot", is_enabled: true, models: [] },
          { provider: "Anthropic", icon: "Bot", is_enabled: true, models: [] },
        ],
        isLoading: false,
        isFetching: false,
      });

      render(<ProviderList modelType="all" />);

      expect(
        screen.queryByTestId("provider-item-OpenAI"),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByTestId("provider-item-Anthropic"),
      ).not.toBeInTheDocument();
    });
  });

  describe("Selection", () => {
    it("should call onProviderSelect when provider is clicked", () => {
      const onProviderSelect = jest.fn();

      render(
        <ProviderList modelType="all" onProviderSelect={onProviderSelect} />,
      );

      screen.getByTestId("provider-item-Ollama").click();

      expect(onProviderSelect).toHaveBeenCalled();
    });

    it("should pass selectedProviderName to items", () => {
      render(<ProviderList modelType="all" selectedProviderName="Ollama" />);

      const ollamaItem = screen.getByTestId("provider-item-Ollama");
      expect(ollamaItem).toHaveAttribute("data-selected", "true");

      const vllmItem = screen.getByTestId("provider-item-vLLM");
      expect(vllmItem).toHaveAttribute("data-selected", "false");
    });
  });

  describe("Search filtering", () => {
    it("should render every provider when the query is empty", () => {
      render(<ProviderList modelType="all" query="" />);

      expect(screen.getByTestId("provider-item-Ollama")).toBeInTheDocument();
      expect(screen.getByTestId("provider-item-vLLM")).toBeInTheDocument();
    });

    it("should filter providers by case-insensitive substring match", () => {
      render(<ProviderList modelType="all" query="OLLAMA" />);

      expect(
        screen.queryByTestId("provider-item-vLLM"),
      ).not.toBeInTheDocument();
      expect(screen.getByTestId("provider-item-Ollama")).toBeInTheDocument();
    });

    it("should show the no-results message when nothing matches", () => {
      render(<ProviderList modelType="all" query="xyzzy" />);

      expect(screen.queryByTestId("provider-list")).not.toBeInTheDocument();
      expect(screen.getByTestId("provider-list-empty")).toBeInTheDocument();
    });

    it("should ignore leading and trailing whitespace in the query", () => {
      render(<ProviderList modelType="all" query="  vllm  " />);

      expect(screen.getByTestId("provider-item-vLLM")).toBeInTheDocument();
      expect(
        screen.queryByTestId("provider-item-Ollama"),
      ).not.toBeInTheDocument();
    });
  });
});
