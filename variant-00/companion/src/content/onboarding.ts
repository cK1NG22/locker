export const ONBOARDING_STEPS = [
  {
    title: "Welcome to Locker",
    description:
      "Locker gives your AI assistant team-specific skills — shared instructions that make it smarter about your workflows, standards, and processes.",
  },
  {
    title: "How it works",
    panels: [
      {
        heading: "Admin uploads skills",
        detail: "Your team admin creates and manages reusable skill instructions in the Locker dashboard.",
      },
      {
        heading: "You connect",
        detail: "Enter your team token here to link your AI assistant to your team's skill library.",
      },
      {
        heading: "Skills power your AI",
        detail: "When you invoke a skill, your AI assistant follows those instructions — no copy-pasting needed.",
      },
    ],
  },
  {
    title: "Connect your team",
    description: "Paste the team token your admin gave you to get started.",
  },
  {
    title: "You're all set!",
    description: "Your AI assistant now has access to your team's skills. Browse them below.",
  },
] as const;

export const STEP_LABELS = ["Welcome", "How it works", "Connect", "Done"];
