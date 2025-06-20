import * as React from "react";
import { cn } from "../../modules/core/utils/cn";

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          "flex min-h-[80px] w-full rounded-md border border-secondary-200 bg-white px-3 py-2 text-sm text-secondary-900 ring-offset-white placeholder:text-secondary-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:border-secondary-800 dark:bg-secondary-950 dark:text-secondary-50 dark:ring-offset-secondary-950 dark:placeholder:text-secondary-500 dark:focus-visible:ring-primary-600",
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Textarea.displayName = "Textarea";

export { Textarea }; 