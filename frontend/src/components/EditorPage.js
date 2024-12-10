"use client";

const { useState } = require("react");
import TinyEditor from "./TinyEditor";

const EditorPage = () => {
  const [content, setContent] = useState("");

  return (
    <>
      <TinyEditor id="tiny-editor" value={content} setValue={setContent} />
      <hr />
      <div dangerouslySetInnerHTML={{ __html: content }} />
    </>
  );
};

export default EditorPage;
