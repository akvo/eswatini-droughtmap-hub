"use client";

import { useAppContext, useAppDispatch } from "@/context/AppContextProvider";
import { api } from "@/lib";
import { Checkbox, Flex, Form, Tag, Input, Button, Modal, Space } from "antd";
import classNames from "classnames";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

const { Search } = Input;
const { useForm } = Form;

const ReviewList = ({ id, dataSource = [], isCompleted = false }) => {
  const { administrations, activeAdm } = useAppContext();
  const [form] = useForm();
  const [marking, setMarking] = useState(false);
  const [search, setSearch] = useState(null);
  const router = useRouter();
  const appDispatch = useAppDispatch();

  const onOpen = (data) => {
    appDispatch({
      type: "SET_ACTIVE_ADM",
      payload: data,
    });
  };

  const onCheckAll = (e) => {
    const isChecked = e.target.checked;
    appDispatch({
      type: "SET_IS_BULK_ACTION",
      payload: isChecked,
    });
    const admValues = form
      .getFieldValue("administrations")
      .map((a) => ({ ...a, checked: isChecked }));
    form.setFieldValue("administrations", admValues);
  };

  const onCheckAdm = (e, administration_id = 0) => {
    const isChecked = e.target.checked;
    appDispatch({
      type: isChecked ? "ADD_SELECTED_ADM" : "REMOVE_SELECTED_ADM",
      payload: parseInt(administration_id, 10),
    });
  };

  const onMarkAll = async () => {
    setMarking(true);
    try {
      const admValues = form.getFieldValue("administrations").map((a) => {
        if (a?.checked) {
          return {
            ...a,
            category: a?.category || a?.initial_category,
            reviewed: true,
          };
        }
        return a;
      });
      await api("PUT", `/reviewer/review/${id}`, {
        suggestion_values: admValues.map(({ name: _, ...a }) => a),
      });
      appDispatch({
        type: "REFRESH_MAP_TRUE",
      });
      setTimeout(() => {
        appDispatch({
          type: "REFRESH_MAP_FALSE",
        });
      }, 500);
      form.setFieldValue("administrations", admValues);
      setMarking(false);
      router.refresh(`/reviews/${id}`);
    } catch (err) {
      setMarking(false);
      console.error(err);
    }
  };

  const resetState = useCallback(() => {
    /**
     * Reset all selected administrations at first render time
     **/
    appDispatch({
      type: "RESET_SELECTED_ADM",
    });
  }, [appDispatch]);

  useEffect(() => {
    resetState();
  }, [resetState]);

  if (!administrations?.length) {
    return null;
  }

  return (
    <div className="h-[calc(100vh-160px)] overflow-y-scroll">
      <Form
        form={form}
        initialValues={{
          administrations: administrations?.map((a) => {
            const findData =
              dataSource.find(
                (d) => d?.administration_id === a?.administration_id
              ) || {};
            return {
              ...a,
              ...findData,
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
                <Search
                  placeholder="Search Inkhundla"
                  onSearch={setSearch}
                  onClear={() => setSearch(null)}
                  allowClear
                />
                {!isCompleted && (
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
                )}
              </div>
              <Form.List name="administrations">
                {(fields) => (
                  <div className="w-full">
                    {fields
                      .filter((f) => {
                        if (search) {
                          return formInstance
                            .getFieldValue(["administrations", f.name, "name"])
                            ?.toLowerCase()
                            ?.includes(search?.toLowerCase());
                        }
                        return f;
                      })
                      .map((field) => {
                        const isReviewed = formInstance.getFieldValue([
                          "administrations",
                          field.name,
                          "reviewed",
                        ]);
                        return (
                          <div
                            className={classNames(
                              "w-full flex flex-row flex-wrap items-center justify-between px-4 py-2 border-b border-neutral-200",
                              {
                                "bg-neutral-100": isReviewed,
                              }
                            )}
                            key={field.key}
                          >
                            <Space>
                              {!isCompleted && (
                                <Form.Item
                                  valuePropName="checked"
                                  name={[field.name, "checked"]}
                                >
                                  <Checkbox
                                    onClick={(e) =>
                                      onCheckAdm(
                                        e,
                                        formInstance.getFieldValue([
                                          "administrations",
                                          field.name,
                                          "administration_id",
                                        ])
                                      )
                                    }
                                  />
                                </Form.Item>
                              )}
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
                            </Space>
                            <div>
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
