import { Can } from "@/components";

const PublicationsPage = () => {
  return (
    <div className="w-full h-auto space-y-4">
      <p>You are signed in as an Admin</p>
      <ul>
        <Can I="create" a="Publication">
          <li>Yes, you can create a Publication</li>
        </Can>
        <Can I="update" a="Publication">
          <li>Yes, you can edit a Publication</li>
        </Can>
        <Can I="delete" a="Publication">
          <li>Yes, you can delete a Publication</li>
        </Can>
        <Can I="update" a="Review">
          <li>Yes, you can edit a Review</li>
        </Can>
        <Can I="delete" a="Review">
          <li>Yes, you can delete a Review</li>
        </Can>
      </ul>
    </div>
  );
};

export default PublicationsPage;
