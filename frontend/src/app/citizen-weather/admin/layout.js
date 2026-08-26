import { UserContextProvider } from "@/context";
import { auth } from "@/lib";

const CitizenWeatherAdminLayout = async ({ children }) => {
  const session = await auth.getSession();
  const abilities = session?.abilities || [];
  return (
    <UserContextProvider {...session} abilities={abilities}>
      {children}
    </UserContextProvider>
  );
};

export default CitizenWeatherAdminLayout;
