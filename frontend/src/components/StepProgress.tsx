import { useState, useEffect } from "react";

interface Step {
  label: string;
  duration: number;
}

interface StepProgressProps {
  steps: Step[];
  active: boolean;
}

export function StepProgress({ steps, active }: StepProgressProps) {
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    if (!active) {
      setCurrentStep(0);
      return;
    }
    if (currentStep >= steps.length - 1) return;

    const timer = setTimeout(() => {
      setCurrentStep((prev) => Math.min(prev + 1, steps.length - 1));
    }, steps[currentStep].duration);

    return () => clearTimeout(timer);
  }, [active, currentStep, steps]);

  if (!active) return null;

  return (
    <div className="space-y-2 py-2">
      {steps.map((step, i) => (
        <div key={i} className="flex items-center gap-2 text-sm">
          {i < currentStep ? (
            <svg className="w-4 h-4 text-green-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          ) : i === currentStep ? (
            <svg className="w-4 h-4 text-blue-500 animate-spin flex-shrink-0" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          ) : (
            <div className="w-4 h-4 rounded-full border-2 border-gray-300 flex-shrink-0" />
          )}
          <span className={i === currentStep ? "text-blue-700 font-medium" : i < currentStep ? "text-green-700" : "text-gray-400"}>
            {step.label}
          </span>
        </div>
      ))}
    </div>
  );
}
