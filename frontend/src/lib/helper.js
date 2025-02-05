export const transformReviews = (
  administrations = [],
  reviews = [],
  users = [],
  publication = {}
) => {
  return administrations
    ?.map((a) => {
      const initial_category = publication?.initial_values?.find(
        (v) => v?.administration_id === a?.administration_id
      )?.category;
      const category = publication?.validated_values?.find(
        (v) => v?.administration_id === a?.administration_id
      )?.category;
      const twgMapping = users?.reduce((acc, prev) => {
        const findCategory = reviews?.find(
          (r) =>
            r?.user_id === prev.id &&
            r?.administration_id === a?.administration_id
        );
        acc[prev.id] = findCategory?.category;
        acc[`${prev.id}_comment`] = {
          user: `${prev.name} (${prev.email})`,
          twg: prev.technical_working_group,
          comment: findCategory?.comment,
          category: findCategory?.category,
        };
        return acc;
      }, {});
      return {
        ...a,
        key: a?.administration_id,
        initial_category,
        category,
        ...twgMapping,
      };
    })
    ?.sort((a, b) => a?.name?.localeCompare(b?.name))
    ?.filter((a) => {
      return Object.keys(a)
        .filter((a) => !isNaN(a))
        .filter((k) => a?.[k] !== undefined).length;
    });
};
