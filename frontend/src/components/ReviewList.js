"use client";

import { useAppContext } from "@/context/AppContextProvider";
import { api } from "@/lib";
import { Checkbox, Flex, Form, Tag, Input, Button, Modal } from "antd";
import { useRouter } from "next/navigation";
import { useState } from "react";

const { Search } = Input;
const { useForm } = Form;

const ReviewList = ({ id, suggestions = [], initialValues = [] }) => {
  const { administrations } = useAppContext();
  const [form] = useForm();
  const [marking, setMarking] = useState(false);
  const router = useRouter();

  const onOpen = (data) => {
    Modal.info({
      title: data?.name,
      content: (
        <ul>
          <li>
            <strong>Category</strong>: {data?.category}
          </li>
          <li>
            <strong>value</strong>: {data?.value}
          </li>
        </ul>
      ),
    });
  };

  const onCheckAll = (e) => {
    const isChecked = e.target.checked;
    const admValues = form
      .getFieldValue("administrations")
      .map((a) => ({ ...a, checked: isChecked }));
    form.setFieldValue("administrations", admValues);
  };

  const onMarkAll = async () => {
    setMarking(true);
    try {
      const admValues = form.getFieldValue("administrations").map((a) => {
        if (a?.checked) {
          return { ...a, reviewed: true };
        }
        return a;
      });
      await api("PUT", `/reviewer/review/${id}`, {
        suggestion_values: admValues,
      });
      form.setFieldValue("administrations", admValues);
      setMarking(false);
      router.refresh(`/reviews/${id}`);
    } catch (err) {
      setMarking(false);
      console.error(err);
    }
  };

  if (!administrations?.length) {
    return null;
  }

  return (
    <div className="h-[calc(100vh-160px)] overflow-y-scroll">
      <Form
        form={form}
        initialValues={{
          administrations: administrations?.map((a) => {
            const initial =
              initialValues?.find(
                (i) => i?.administration_id === a?.administration_id
              ) || {};
            const suggestion =
              suggestions?.find(
                (d) => d?.administration_id === a?.administration_id
              ) || {};
            return {
              ...a,
              ...initial,
              ...suggestion,
              checked: false,
            };
          }),
        }}
      >
        {(_, formInstance) => {
          const numberChecked = formInstance
            .getFieldValue("administrations")
            ?.filter((a) => a?.checked)?.length;

          return (
            <>
              <div className="p-4 sticky top-0 left-0 border-b border-neutral-200 bg-neutral-100 space-y-4 z-50">
                <Search />
                <Flex align="center" justify="space-between">
                  <Checkbox onChange={onCheckAll} />
                  <div>
                    <Button
                      size="small"
                      disabled={numberChecked === 0}
                      onClick={onMarkAll}
                      loading={marking}
                    >{`Mark as Reviewed ${
                      numberChecked ? `(${numberChecked})` : ""
                    }`}</Button>
                  </div>
                </Flex>
              </div>
              <Form.List name="administrations">
                {(fields) => (
                  <div className="w-full px-4">
                    {fields.map((field) => {
                      const isReviewed = formInstance.getFieldValue([
                        "administrations",
                        field.name,
                        "reviewed",
                      ]);
                      return (
                        <div
                          className="w-full flex flex-row flex-wrap items-start justify-between"
                          key={field.key}
                        >
                          <div className="flex">
                            <Form.Item
                              valuePropName="checked"
                              name={[field.name, "checked"]}
                            >
                              <Checkbox />
                            </Form.Item>
                            <Button
                              onClick={() =>
                                onOpen(
                                  formInstance.getFieldValue([
                                    "administrations",
                                    field.name,
                                  ])
                                )
                              }
                              type="link"
                            >
                              {formInstance.getFieldValue([
                                "administrations",
                                field.name,
                                "name",
                              ])}
                            </Button>
                          </div>
                          <div className="pt-2">
                            <Tag color={isReviewed ? "success" : null}>
                              {isReviewed ? "Reviewed" : "Pending"}
                            </Tag>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </Form.List>
            </>
          );
        }}
      </Form>
    </div>
  );
};

export default ReviewList;
