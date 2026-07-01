import { UserContextProvider } from "@/context";
import { auth } from "@/lib";

const PublicationLayout = async ({ children }) => {
  const session = await auth.getSession();
  const abilities = session?.abilities || [];
  return (
    <UserContextProvider abilities={abilities}>{children}</UserContextProvider>
  );
};

export default PublicationLayout;
