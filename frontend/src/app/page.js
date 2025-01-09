import { Button } from "antd";
import dynamic from "next/dynamic";
import { auth } from "@/lib";
import Link from "next/link";

const ExampleMap = dynamic(() => import("../components/Map/ExampleMap"), {
  ssr: false,
});

export const Navbar = ({ session = null }) => (
  <div className="w-full py-2 bg-primary">
    <div className="w-full container flex flex-row justify-end items-center">
      <nav className="w-fit px-4">
        {session ? (
          <Link href={"/profile"}>
            <Button>Profile</Button>
          </Link>
        ) : (
          <Link href={"/login"}>
            <Button type="primary">Login</Button>
          </Link>
        )}
      </nav>
    </div>
  </div>
);

const Home = async () => {
  const session = await auth.getSession();
  return (
    <div className="w-full h-screen">
      <Navbar session={session} />
      <div className="w-full h-full">
        <ExampleMap />
      </div>
    </div>
  );
};

export default Home;
