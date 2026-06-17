import LgxChat from "@extensions/lgx/ui/pages/lgx_chat";
import { useEffect } from "react";

interface Portfolio {
  name: string;
  portfolio_id: string;
  orgs: Record<string, Org>;
  tools: Record<string, Tool>;
}

interface Org {
  name: string;
  org_id: string;
  tools: string[];
}

interface Tool {
  name: string;
  handle: string;
}

export default function LGX({
  portfolio,
  org,
  tool,
  section,
  tree,
  onNavigate,
}: {
  portfolio: string;
  org: string;
  tool: string;
  section?: string;
  tree?: { portfolios: Record<string, Portfolio> };
  onNavigate?: (path: string) => void;
}) {
  useEffect(() => {
    if (!section && onNavigate) {
      onNavigate(`/${portfolio}/${org}/${tool}/chat`);
    }
  }, [section, portfolio, org, tool, onNavigate]);

  if (!section) {
    return null;
  }

  return (
    <div className="flex min-h-screen w-full flex-col bg-muted/40">
      <div className="flex flex-col sm:gap-2 sm:pl-2">
        {section === "chat" && (
          <LgxChat
            portfolio={portfolio}
            org={org}
            tool={tool}
            tree={tree}
            onNavigate={onNavigate ?? (() => {})}
          />
        )}
      </div>
    </div>
  );
}
