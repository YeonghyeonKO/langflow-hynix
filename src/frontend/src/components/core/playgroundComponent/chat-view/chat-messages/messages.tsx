import { Loader2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef } from "react";
import { StickToBottom, useStickToBottomContext } from "use-stick-to-bottom";
import { SafariScrollFix } from "@/components/common/safari-scroll-fix";
import useFlowStore from "@/stores/flowStore";
import { usePlaygroundStore } from "@/stores/playgroundStore";
import type { ChatMessageType } from "@/types/chat";
import { cn } from "@/utils/utils";
import { BotMessage } from "./components/bot-message";
import ChatMessage from "./components/chat-message";
import { useChatHistory } from "./hooks/use-chat-history";

interface MessagesProps {
  visibleSession: string | null;
  playgroundPage?: boolean;
  updateChat?: (chat: ChatMessageType, message: string) => void;
  closeChat?: () => void;
}

// Placed inside StickToBottom so useStickToBottomContext is available
const LoadMoreTrigger = ({
  hasMore,
  isLoadingMore,
  onLoadMore,
}: {
  hasMore: boolean;
  isLoadingMore: boolean;
  onLoadMore: () => Promise<number>;
}) => {
  const { scrollRef } = useStickToBottomContext();
  const sentinelRef = useRef<HTMLDivElement>(null);
  // The element that actually scrolls the chat. Depending on the surrounding
  // layout, use-stick-to-bottom's scrollRef can end up as a full-height,
  // non-scrolling element while an ancestor does the scrolling. Using that
  // element as the IntersectionObserver root makes the sentinel intersect
  // permanently (the root's box spans the whole content), so the observer
  // fires exactly once and pagination dies — resolve the real scroll parent
  // from the sentinel instead.
  const containerRef = useRef<HTMLElement | null>(null);
  // Guards a load in progress. Local to the effect chain so a chained load
  // can proceed without waiting for the isLoadingMore state to flush.
  const loadingRef = useRef(false);
  // The sentinel sits at the top of the list, so it can be visible while the
  // playground opens — before the view is pinned to the bottom. Loading in
  // that window cascades through the entire history on open. Only arm
  // pagination once the list overflows and the view has actually landed at
  // the bottom; after that, loads can only be triggered by scrolling up.
  const armedRef = useRef(false);

  // Keep stable refs to avoid recreating the observer on every render
  const hasMoreRef = useRef(hasMore);
  hasMoreRef.current = hasMore;
  const onLoadMoreRef = useRef(onLoadMore);
  onLoadMoreRef.current = onLoadMore;

  // Load a page, then restore scroll position so the newly prepended messages
  // push the sentinel back out of view. use-stick-to-bottom applies
  // `overflow-anchor: none`, so without this the sentinel stays visible, the
  // IntersectionObserver never re-fires (no true->false->true transition), and
  // pagination deadlocks after a single page. If the sentinel is still visible
  // after restoring (short messages), chain another load.
  const runLoad = useCallback(async () => {
    const container = containerRef.current;
    const sentinel = sentinelRef.current;
    if (
      !container ||
      !sentinel ||
      loadingRef.current ||
      !hasMoreRef.current ||
      !armedRef.current
    ) {
      return;
    }

    // Re-check with fresh geometry: observer entries can arrive after the
    // initial pin-to-bottom has already pushed the sentinel out of view.
    {
      const cRect = container.getBoundingClientRect();
      const sRect = sentinel.getBoundingClientRect();
      const sentinelVisible =
        sRect.bottom >= cRect.top && sRect.top <= cRect.bottom;
      if (!sentinelVisible) {
        return;
      }
    }

    loadingRef.current = true;
    try {
      const prevHeight = container.scrollHeight;
      const prevTop = container.scrollTop;

      const loaded = await onLoadMoreRef.current();

      if (loaded > 0) {
        // Wait for the DOM to commit the prepended nodes before measuring.
        await new Promise<void>((resolve) => {
          requestAnimationFrame(() => requestAnimationFrame(() => resolve()));
        });
        const delta = container.scrollHeight - prevHeight;
        container.scrollTop = prevTop + delta;

        // If the sentinel is still within the viewport after restoring, keep
        // loading so short content can't strand the user mid-history.
        const cRect = container.getBoundingClientRect();
        const sRect = sentinel.getBoundingClientRect();
        if (
          sRect.bottom >= cRect.top &&
          sRect.top <= cRect.bottom &&
          hasMoreRef.current
        ) {
          loadingRef.current = false;
          void runLoad();
          return;
        }
      }
    } finally {
      loadingRef.current = false;
    }
  }, []);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;

    // Resolve the element that actually scrolls: nearest ancestor with a
    // scrollable overflow-y that is really clipping its content. An ancestor
    // can carry overflow-y:auto while its height grows with the content (so
    // it never scrolls) — skip those, they are exactly the trap scrollRef
    // falls into. Fall back to the first overflow-styled ancestor, then to
    // stick-to-bottom's scrollRef.
    let clipping: HTMLElement | null = null;
    let styled: HTMLElement | null = null;
    let parent: HTMLElement | null = sentinel.parentElement;
    while (parent) {
      const { overflowY } = getComputedStyle(parent);
      if (
        overflowY === "auto" ||
        overflowY === "scroll" ||
        overflowY === "overlay"
      ) {
        styled = styled ?? parent;
        if (parent.scrollHeight > parent.clientHeight + 1) {
          clipping = parent;
          break;
        }
      }
      parent = parent.parentElement;
    }
    const container = clipping ?? styled ?? scrollRef.current;
    if (!container) return;
    containerRef.current = container;

    const checkArmed = () => {
      if (armedRef.current) return;
      const hasOverflow = container.scrollHeight > container.clientHeight;
      const atBottom =
        container.scrollTop + container.clientHeight >=
        container.scrollHeight - 2;
      if (hasOverflow && atBottom) {
        armedRef.current = true;
      }
    };
    checkArmed();
    container.addEventListener("scroll", checkArmed, { passive: true });

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          void runLoad();
        }
      },
      { root: container, threshold: 0 },
    );
    observer.observe(sentinel);

    return () => {
      container.removeEventListener("scroll", checkArmed);
      observer.disconnect();
    };
  }, [scrollRef, runLoad]);

  if (!hasMore) return null;

  return (
    <div
      ref={sentinelRef}
      className="flex h-8 w-full items-center justify-center"
    >
      {isLoadingMore && (
        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
      )}
    </div>
  );
};

export const Messages = ({
  visibleSession,
  playgroundPage,
  updateChat,
  closeChat,
}: MessagesProps) => {
  const { chatHistory, loadMore, hasMore, isLoadingMore } =
    useChatHistory(visibleSession);
  const isBuilding = useFlowStore((state) => state.isBuilding);
  const isPlaygroundOpen = usePlaygroundStore((state) => state.isOpen);

  const bottomRef = useRef<HTMLDivElement | null>(null);

  // Show thinking placeholder when building and last message is from user (no bot response yet)
  // Only show if the flow has a ChatOutput, otherwise there's nothing to produce a response
  // Select the boolean, not the array: setNodes recreates `outputs` on every
  // call (including node drags), and an array subscription would re-render
  // the whole message list on each drag frame.
  const hasChatOutput = useFlowStore((state) =>
    state.outputs.some((output) => output.type === "ChatOutput"),
  );
  const lastChat = chatHistory[chatHistory.length - 1];
  const showThinkingPlaceholder =
    isBuilding && lastChat?.isSend === true && hasChatOutput;
  const thinkingPlaceholder = useMemo<ChatMessageType>(
    () => ({
      id: "thinking-placeholder",
      message: "",
      isSend: false,
      sender_name: "AI",
      category: "message",
      content_blocks: [],
      timestamp: new Date().toISOString(),
    }),
    [],
  );

  const messagesContent = (
    <div className="flex flex-col flex-grow place-self-center w-full relative overflow-x-hidden">
      {chatHistory && (isBuilding || chatHistory.length > 0) && (
        <>
          <LoadMoreTrigger
            hasMore={hasMore}
            isLoadingMore={isLoadingMore}
            onLoadMore={loadMore}
          />
          {chatHistory.map((chat: ChatMessageType, index) => {
            return (
              <ChatMessage
                key={`${chat.id}-${index}`}
                chat={chat}
                lastMessage={
                  !showThinkingPlaceholder && chatHistory.length - 1 === index
                }
                updateChat={updateChat ?? (() => {})}
                closeChat={closeChat}
                playgroundPage={playgroundPage}
              />
            );
          })}
          {showThinkingPlaceholder && (
            <BotMessage
              chat={thinkingPlaceholder}
              lastMessage={true}
              updateChat={updateChat ?? (() => {})}
              closeChat={closeChat}
              playgroundPage={playgroundPage}
            />
          )}
          {isPlaygroundOpen && (
            <div
              ref={bottomRef}
              className="pointer-events-none absolute bottom-0 left-0 right-0 h-0 w-0 overflow-hidden"
              aria-hidden
            />
          )}
        </>
      )}
    </div>
  );

  return (
    <StickToBottom
      className={cn(
        "flex w-full flex-col rounded-md",
        visibleSession ? "h-[95%]" : "h-full",
      )}
      resize="instant"
      initial="instant"
    >
      <StickToBottom.Content className="flex flex-col min-h-full ">
        {messagesContent}
      </StickToBottom.Content>
      <SafariScrollFix />
    </StickToBottom>
  );
};
