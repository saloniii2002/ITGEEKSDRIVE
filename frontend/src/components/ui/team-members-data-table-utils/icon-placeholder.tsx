import * as React from "react";
import * as LucideIcons from "lucide-react";

interface IconPlaceholderProps extends React.SVGProps<SVGSVGElement> {
  lucide?: string;
  tabler?: string;
  hugeicons?: string;
  phosphor?: string;
  remixicon?: string;
  className?: string;
}

export function IconPlaceholder({
  lucide,
  className,
  ...props
}: IconPlaceholderProps) {
  if (lucide) {
    const IconComponent = (LucideIcons as any)[lucide];
    if (IconComponent) {
      return <IconComponent className={className} {...props} />;
    }
  }
  // Fallback to dot icon
  return <LucideIcons.Circle className={className} {...props} />;
}
