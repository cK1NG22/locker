import type { Skill } from "../hooks/useSkills";
import SkillItem from "./SkillItem";

interface SkillListProps {
  team: string;
  skills: Skill[];
  onChangeToken: () => void;
}

export default function SkillList({ team, skills, onChangeToken }: SkillListProps) {
  return (
    <div className="max-w-lg mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">
            Locker Companion
          </h1>
          <p className="text-sm text-gray-500">
            {team} &middot; {skills.length} skill{skills.length !== 1 ? "s" : ""}
          </p>
        </div>
      </div>

      {skills.length === 0 ? (
        <p className="text-sm text-gray-500 text-center py-8">
          No skills assigned to your team yet.
        </p>
      ) : (
        <div className="space-y-2">
          {skills.map((s) => (
            <SkillItem key={s.name} skill={s} />
          ))}
        </div>
      )}

      <div className="mt-8 text-center">
        <button
          onClick={onChangeToken}
          className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
        >
          Change token
        </button>
      </div>
    </div>
  );
}
