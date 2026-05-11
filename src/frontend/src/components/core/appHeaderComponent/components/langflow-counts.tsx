import { HiOutlineGlobeAlt } from "react-icons/hi";
import ShadTooltip from "@/components/common/shadTooltipComponent";
import { Button } from "@/components/ui/button";
import { useUtilityStore } from "@/stores/utilityStore";

export const LangflowCounts = () => {
  const agentHubUrl: string = useUtilityStore((state) => state.agentHubUrl);

  if (!agentHubUrl) return null;

  return (
    <div className="flex items-center gap-3">
      <ShadTooltip
        content="Go to Agent Hub"
        side="bottom"
        styleClasses="z-10"
      >
        <Button
          unstyled
          onClick={() => window.open(agentHubUrl, "_blank")}
          className="hit-area-hover flex items-center gap-2 rounded-md p-1 text-muted-foreground"
        >
          <div className="relative items-center rounded-md px-2 py-1 flex">
            <HiOutlineGlobeAlt className="h-4 w-4" />
            <span className="text-xs font-semibold pl-2">Agent Hub</span>
          </div>
        </Button>
      </ShadTooltip>
    </div>
  );
};

export default LangflowCounts;
