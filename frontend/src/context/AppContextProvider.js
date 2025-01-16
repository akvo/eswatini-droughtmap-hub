"use client";

import { createContext, useContext, useReducer } from "react";

const AppContext = createContext(null);
const AppDispatchContext = createContext(null);
const initialValues = {
  administrations: [],
  geoData: null,
};

const appReducer = (state, action) => {
  switch (action.type) {
    case "SET_ADM":
      return {
        ...state,
        administrations: action.payload,
      };
    case "SET_GEODATA":
      return {
        ...state,
        geoData: action.payload,
      };
    default:
      throw Error(
        `Unknown action: ${action.type}. Action type must be CAPITAL text.`
      );
  }
};

const AppContextProvider = ({ children }) => {
  const [value, dispatch] = useReducer(appReducer, initialValues);

  return (
    <AppContext.Provider value={value}>
      <AppDispatchContext.Provider value={dispatch}>
        {children}
      </AppDispatchContext.Provider>
    </AppContext.Provider>
  );
};

export const useAppContext = () => useContext(AppContext);
export const useAppDispatch = () => useContext(AppDispatchContext);

export default AppContextProvider;
