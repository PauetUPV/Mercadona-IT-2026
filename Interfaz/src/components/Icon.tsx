import type { ReactNode } from "react";

export type IconName =
  | "home"
  | "grid"
  | "list"
  | "user"
  | "search"
  | "cart"
  | "send"
  | "mic"
  | "stop"
  | "smile"
  | "chef"
  | "plus"
  | "check"
  | "back";

export function Icon({
  name,
  size = 24,
  strokeWidth = 1.8,
}: {
  name: IconName;
  size?: number;
  strokeWidth?: number;
}) {
  const paths: Record<IconName, ReactNode> = {
    home: (
      <>
        <path d="m3 10.8 9-7.3 9 7.3" />
        <path d="M5.5 9.7v10.8h13V9.7M9.2 20.5v-6.2h5.6v6.2" />
      </>
    ),
    grid: (
      <>
        <rect x="3" y="3" width="7" height="7" rx="1.4" />
        <rect x="14" y="3" width="7" height="7" rx="1.4" />
        <rect x="3" y="14" width="7" height="7" rx="1.4" />
        <rect x="14" y="14" width="7" height="7" rx="1.4" />
      </>
    ),
    list: (
      <>
        <path d="M9 6h12M9 12h12M9 18h12" />
        <path d="M3.5 6h.01M3.5 12h.01M3.5 18h.01" strokeWidth="3.2" />
      </>
    ),
    user: (
      <>
        <circle cx="12" cy="8" r="4" />
        <path d="M4.5 21a7.5 7.5 0 0 1 15 0" />
      </>
    ),
    search: (
      <>
        <circle cx="10.7" cy="10.7" r="6.7" />
        <path d="m16 16 4.5 4.5" />
      </>
    ),
    cart: (
      <>
        <path d="M3 4h2l2.2 10.2a2 2 0 0 0 2 1.6h7.9a2 2 0 0 0 1.9-1.5L20.5 8H6" />
        <circle cx="9.5" cy="20" r="1" fill="currentColor" stroke="none" />
        <circle cx="17.5" cy="20" r="1" fill="currentColor" stroke="none" />
      </>
    ),
    send: (
      <>
        <path d="m21 3-7.5 18-3.2-7.3L3 10.5 21 3Z" />
        <path d="m10.3 13.7 4.5-4.5" />
      </>
    ),
    mic: (
      <>
        <rect x="9" y="2.5" width="6" height="11.5" rx="3" />
        <path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21.5" />
      </>
    ),
    stop: <rect x="6.5" y="6.5" width="11" height="11" rx="2.5" fill="currentColor" stroke="none" />,
    smile: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M8 14.5a5 5 0 0 0 8 0M9 9h.01M15 9h.01" />
      </>
    ),
    chef: (
      <>
        <path d="M7 10.5a4 4 0 0 1 .7-7.9A4.8 4.8 0 0 1 12 1a4.8 4.8 0 0 1 4.3 1.6 4 4 0 0 1 .7 7.9V20H7v-9.5Z" />
        <path d="M7 14h10" />
      </>
    ),
    plus: (
      <>
        <path d="M12 5v14M5 12h14" />
      </>
    ),
    check: (
      <>
        <path d="m5 12.5 4.5 4.5L19 7.5" />
      </>
    ),
    back: (
      <>
        <path d="m15 5-7 7 7 7" />
      </>
    ),
  };

  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={strokeWidth}
    >
      {paths[name]}
    </svg>
  );
}
