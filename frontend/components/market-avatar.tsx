import {
  Bitcoin,
  Briefcase,
  ChartLine,
  Clapperboard,
  Cpu,
  FlaskConical,
  Globe,
  Landmark,
  Sparkles,
  Trophy,
  type LucideIcon,
} from "lucide-react";
import Image from "next/image";

import { cn } from "@/lib/format";

const CATEGORY_STYLE: Record<string, { icon: LucideIcon; hue: number }> = {
  politics: { icon: Landmark, hue: 260 },
  world: { icon: Globe, hue: 200 },
  crypto: { icon: Bitcoin, hue: 60 },
  economy: { icon: ChartLine, hue: 160 },
  economics: { icon: ChartLine, hue: 160 },
  business: { icon: Briefcase, hue: 220 },
  tech: { icon: Cpu, hue: 290 },
  science: { icon: FlaskConical, hue: 180 },
  sports: { icon: Trophy, hue: 30 },
  culture: { icon: Clapperboard, hue: 340 },
};
const FALLBACK = { icon: Sparkles, hue: 290 };

export function MarketAvatar({
  imageUrl,
  question,
  category = "",
  size = 40,
  className,
}: {
  imageUrl: string | null;
  question: string;
  category?: string;
  size?: number;
  className?: string;
}) {
  const style = { width: size, height: size };
  if (imageUrl) {
    return (
      <Image
        src={imageUrl}
        alt={question}
        width={size}
        height={size}
        className={cn("shrink-0 rounded-lg object-cover ring-1 ring-white/10", className)}
        style={style}
      />
    );
  }
  const { icon: Icon, hue } = CATEGORY_STYLE[category] ?? FALLBACK;
  return (
    <div
      aria-hidden
      className={cn("grid shrink-0 place-items-center rounded-lg text-sm font-semibold ring-1 ring-white/10", className)}
      style={{
        ...style,
        background: `linear-gradient(135deg, oklch(0.55 0.16 ${hue}), oklch(0.3 0.1 ${hue + 40}))`,
      }}
    >
      <Icon style={{ width: size * 0.45, height: size * 0.45 }} className="text-white/90" />
    </div>
  );
}
