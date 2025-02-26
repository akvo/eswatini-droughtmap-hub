import { Navbar } from "@/components";
import { auth } from "@/lib";

const ComparePage = async () => {
  const session = await auth.getSession();
  return (
    <div className="w-full min-h-screen">
      <Navbar session={session} />
    </div>
  );
};

export default ComparePage;
