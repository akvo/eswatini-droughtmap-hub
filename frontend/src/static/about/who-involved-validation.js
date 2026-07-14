import { ReviewIcon } from "./icons";

export const whoInvolvedValidationConfig = {
  title: "Who is Involved in Validation?",
  description:
    "The Technical Working Group (TWG) - comprising representatives from Eswatini\u2019s NDMA, the Ministry of Agriculture, MET, Department of Water Affairs (DWA) and the University of Eswatini (UNESWA) - plays a crucial role in the review and validation process. Their responsibilities include:",
  children: [
    {
      icon: ReviewIcon,
      title: "Reviewing the generated maps monthly.",
    },
    {
      icon: ReviewIcon,
      title: "Benchmarking against other datasets and around reports.",
    },
    {
      icon: ReviewIcon,
      title: "Approving or requesting changes before publication.",
    },
  ],
  image_url: "/images/about-validation.jpg",
};
