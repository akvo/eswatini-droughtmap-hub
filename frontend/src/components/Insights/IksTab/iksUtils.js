import { IKS_INDICATOR_CATALOGUE } from "@/static/config";

export const formatPercentage = (val) => {
  if (val === null || val === undefined) return "0";
  const num = Number(val);
  if (isNaN(num)) return "0";
  if (num % 1 === 0) return num.toString();
  return Number(num.toFixed(2)).toString();
};

export const getRainfallPredictors = () => {
  const birds = [];
  const insects = [];
  const plants = [];
  const sky = [];

  Object.keys(IKS_INDICATOR_CATALOGUE).forEach((key) => {
    const item = IKS_INDICATOR_CATALOGUE[key];
    if (item.type === "rainfall") {
      const num = parseInt(key.split("__")[0], 10);
      const indicatorObj = {
        dbKey: key,
        name: item.label,
        isDroughtLeaning: item.meaning === "drought",
      };
      if (num <= 9) birds.push(indicatorObj);
      else if (num <= 12) insects.push(indicatorObj);
      else if (num <= 16) plants.push(indicatorObj);
      else sky.push(indicatorObj);
    }
  });

  return [
    { key: "b-birds", header: "Birds (Tinyoni)", indicators: birds },
    { key: "b-insects", header: "Insects & animals", indicators: insects },
    { key: "b-plants", header: "Plants & fruits", indicators: plants },
    { key: "b-sky", header: "Atmosphere & sky", indicators: sky },
  ];
};

export const getSeasonalPredictors = () => {
  const animals = [];
  const plants = [];

  Object.keys(IKS_INDICATOR_CATALOGUE).forEach((key) => {
    const item = IKS_INDICATOR_CATALOGUE[key];
    if (item.type === "seasonal") {
      const num = parseInt(key.split("__")[0], 10);
      const indicatorObj = {
        dbKey: key,
        name: item.label,
        isDroughtLeaning: item.meaning === "drought",
      };
      if (num <= 5) animals.push(indicatorObj);
      else plants.push(indicatorObj);
    }
  });

  return [
    { key: "c-animals", header: "Birds & Animals", indicators: animals },
    { key: "c-plants", header: "Plants", indicators: plants },
  ];
};
