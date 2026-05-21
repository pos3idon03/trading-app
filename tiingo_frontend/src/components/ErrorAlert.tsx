export default function ErrorAlert({
  message,
  children,
}: {
  message: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="bg-red-900/30 border border-red-700 text-red-200 px-4 py-3 rounded-lg text-sm">
      {message}
      {children}
    </div>
  );
}
