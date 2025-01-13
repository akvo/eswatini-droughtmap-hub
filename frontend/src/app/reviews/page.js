"use client";

import { Can } from "@/components";

class Entity {
  constructor(attrs) {
    Object.assign(this, attrs);
  }
}

class Review extends Entity {}

const ReviewsPage = () => {
  const someoneReview = new Review({ owner: "false" });
  const myReview = new Review({ owner: "true" });
  return (
    <div className="w-full h-auto space-y-4">
      <p>You are signed in as a Reviewer</p>

      <ul>
        <Can I="create" a="Review">
          <li>Yes, you can create a review</li>
        </Can>
        <Can I="create" a="Publication">
          <li>
            <del>No, you can't</del>
          </li>
        </Can>
        <Can I="read" a="Publication">
          <li>Yes, you can read Publication</li>
        </Can>
        <Can I="update" a={someoneReview}>
          <li>No, you can't</li>
        </Can>
        <Can I="update" a={myReview}>
          <li>Yes, you can update your Review</li>
        </Can>
      </ul>
    </div>
  );
};

export default ReviewsPage;
