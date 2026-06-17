import { MessagesSquare } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface ToolMenuProps {
  portfolio: string;
  org: string;
  tool?: string;
  section?: string;
  onNavigate: (path: string) => void;
}

export default function LGXSideNav({
  portfolio,
  org,
  tool,
  section,
  onNavigate,
}: ToolMenuProps) {
  return (
    <nav
      className={
        !org || org === "settings"
          ? "hidden"
          : "flex flex-col items-center gap-1 px-1 sm:py-4"
      }
    >
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex flex-col items-center">
              <button
                onClick={() => onNavigate(`/${portfolio}/${org}/${tool}/chat`)}
                className={
                  section === "chat"
                    ? "group flex h-9 w-9 shrink-0 items-center justify-center gap-2 rounded-full bg-gray-200 text-lg font-semibold text-muted-foreground md:h-12 md:w-12 md:text-base"
                    : "flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:text-foreground md:h-8 md:w-8"
                }
              >
                <MessagesSquare className="h-5 w-5" color="#6366f1" />
                <span className="sr-only">Chat</span>
              </button>
              <span className="text-xxs">Chat</span>
            </div>
          </TooltipTrigger>
          <TooltipContent side="right">LGX Chat</TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </nav>
  );
}
