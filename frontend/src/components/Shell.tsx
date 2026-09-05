import { Bell, Compass, LayoutGrid, Orbit, Settings, UserRound, Waypoints } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { api } from "../lib/api";

const nav = [
  { to: "/", label: "Today", icon: LayoutGrid, end: true },
  { to: "/pipeline", label: "Pipeline", icon: Waypoints },
  { to: "/signals", label: "Signals", icon: Bell },
  { to: "/discover", label: "Discover", icon: Compass },
  { to: "/profile", label: "Profile", icon: UserRound },
  { to: "/settings", label: "Settings", icon: Settings },
];

export default function Shell() {
  const [unread, setUnread] = useState(0);
  useEffect(() => {
    const tick = () => api.dashboard().then((d) => setUnread(d.unread_alerts)).catch(() => {});
    tick();
    const t = setInterval(tick, 60_000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="min-h-screen md:grid md:grid-cols-[220px_1fr]">
      <aside className="border-b md:border-b-0 md:border-r border-line px-4 py-5 md:sticky md:top-0 md:h-screen flex md:flex-col gap-6 items-center md:items-stretch">
        <div className="flex items-center gap-2 font-display font-semibold text-lg">
          <Orbit className="text-signal" size={22} /> Orbit
        </div>
        <nav className="flex md:flex-col gap-1 flex-1 overflow-x-auto">
          {nav.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm whitespace-nowrap transition-colors ${
                  isActive ? "bg-panel text-ink" : "text-dim hover:text-ink"
                }`
              }
            >
              <Icon size={18} />
              <span>{label}</span>
              {label === "Signals" && unread > 0 && (
                <span className="ml-auto rounded-full bg-amber text-void text-xs px-1.5 font-semibold">{unread}</span>
              )}
            </NavLink>
          ))}
        </nav>
        <p className="hidden md:block text-xs text-dim">Checks your inbox and job boards every morning.</p>
      </aside>
      <main className="px-5 py-6 md:px-10 md:py-8 max-w-6xl w-full">
        <Outlet />
      </main>
    </div>
  );
}
