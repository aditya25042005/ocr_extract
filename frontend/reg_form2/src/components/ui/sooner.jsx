"use client"

import {
  CircleCheckIcon,
  InfoIcon,
  Loader2Icon,
  OctagonXIcon,
  TriangleAlertIcon,
} from "lucide-react"
// Assuming useTheme is correctly imported and available
import { useTheme } from "next-themes" 
// Sonner is typically imported as Toaster, but we'll stick to your alias
import { Toaster as Sonner } from "sonner"

const Toaster = (props) => {
  // Destructure the theme from next-themes, defaulting to "system"
  const { theme = "system" } = useTheme()

  return (
    <Sonner
      // The theme needs to be passed, ensuring it's one of Sonner's accepted themes
      theme={theme}
      className="toaster group"
      // ➡️ ADD THIS LINE TO SET THE DEFAULT POSITION TO TOP-RIGHT
      position="top-right"
      // Custom icons using Lucide-React
      icons={{
        success: <CircleCheckIcon className="size-4" />,
        info: <InfoIcon className="size-4" />,
        warning: <TriangleAlertIcon className="size-4" />,
        error: <OctagonXIcon className="size-4" />,
        // Loading icon with animation
        loading: <Loader2Icon className="size-4 animate-spin" />,
      }}
      // Custom styles override Sonner's defaults, mapping them to 
      // your Tailwind/Shadcn UI CSS variables (e.g., --popover, --border)
      style={
        {
          "--normal-bg": "var(--popover)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "var(--border)",
          "--border-radius": "var(--radius)",
        }
      }
      // Pass any remaining props (like position, duration, etc.) to Sonner
      {...props}
    />
  )
}

export { Toaster }

/*
Note: To use this component, you must install the following dependencies:
npm install sonner lucide-react next-themes
*/