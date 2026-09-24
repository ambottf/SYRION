export default function Loading() {
  return (
    <div className="grid" style={{ gap: 12 }}>
      <div className="skeleton" style={{ height: 18, width: "32%" }} />
      <div className="grid grid-3">
        <div className="skeleton" style={{ height: 92 }} />
        <div className="skeleton" style={{ height: 92 }} />
        <div className="skeleton" style={{ height: 92 }} />
      </div>
      <div className="skeleton" style={{ height: 260 }} />
    </div>
  );
}
