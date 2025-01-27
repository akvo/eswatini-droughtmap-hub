"use client";

import { useState } from "react";
import {
  Button,
  Checkbox,
  DatePicker,
  Divider,
  Flex,
  Form,
  Input,
  List,
  message,
  Space,
  Typography,
} from "antd";
import { SubmitButton } from "../Buttons";
import TinyEditor from "../TinyEditor";
import dayjs from "dayjs";
import { useRouter } from "next/navigation";
import { api } from "@/lib";
import { CREATE_PUBLICATION_MAIL } from "@/static/config";

const { Text, Title } = Typography;
const { useForm } = Form;
const { Search } = Input;

const PublicationForm = ({ geonode, reviewer, reviewerList = [] }) => {
  const [search, setSearch] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadMore, setLoadMore] = useState(false);
  const [revPage, setRevPage] = useState(1);
  const [errors, setErrors] = useState([]);
  const [form] = useForm();
  const router = useRouter();

  const loadMoreReviewers =
    reviewer?.total_page > 1 && revPage <= reviewer?.total_page;

  const onLoadReviewers = async () => {
    setLoadMore(true);
    try {
      const { data: newReviewerList, current: currPage } = await api(
        "GET",
        `/admin/reviewers?page=${revPage}`
      );
      setRevPage(currPage);
      form.setFieldValue("reviewers", [
        ...form.getFieldValue("reviewers"),
        ...newReviewerList,
      ]);
      setLoadMore(false);
    } catch (err) {
      console.error(err);
      setLoadMore(false);
    }
  };

  const onFinish = async (values) => {
    setLoading(true);
    try {
      const res = await api("POST", "/admin/publications", {
        ...values,
        cdi_geonode_id: geonode?.pk,
        due_date: dayjs(values?.due_date).format("YYYY-MM-DD"),
        year_month: dayjs(geonode?.year_month).format("YYYY-MM-DD"),
        initial_values: [],
        reviewers: values?.reviewers
          ?.filter((r) => r?.checked)
          ?.map((r) => r?.id),
      });
      if (res?.id) {
        message.success(
          "New publication successfully created and sent to all reviewers."
        );
        router.push("/publications");
      } else {
        setLoading(false);
        setErrors(res);
      }
    } catch (err) {
      console.error(err);
      message.error("[ADM-P-1] Please report this issue along with the code.");
      setLoading(false);
    }
  };

  return (
    <Form
      form={form}
      initialValues={{
        ...geonode,
        reviewers: reviewerList,
        subject: CREATE_PUBLICATION_MAIL?.subject,
        message: CREATE_PUBLICATION_MAIL?.message,
      }}
      onFinish={onFinish}
      layout="vertical"
    >
      {(_, formInstance) => (
        <div className="w-full">
          <div>
            <p>Year month</p>
            <Title level={3}>
              {dayjs(formInstance.getFieldValue("year_month")).format(
                "YYYY-MM"
              )}
            </Title>
          </div>
          <Form.Item
            label="Due date review"
            name="due_date"
            rules={[
              {
                required: true,
              },
            ]}
            help={errors?.due_date?.join(", ")}
            validateStatus={errors?.due_date ? "error" : null}
          >
            <DatePicker
              format={{
                format: "YYYY-MM-DD",
                type: "mask",
              }}
            />
          </Form.Item>
          <Form.Item
            label="Subject"
            name="subject"
            rules={[
              {
                required: true,
              },
            ]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="Message"
            name="message"
            rules={[
              {
                required: true,
              },
            ]}
          >
            <TinyEditor
              value={formInstance.getFieldValue("message")}
              setValue={(v) => formInstance.setFieldValue("message", v)}
              height={300}
            />
          </Form.Item>
          <Divider orientation="left">Select Reviewers</Divider>
          <div className="w-full mb-4">
            <Form.List
              name="reviewers"
              className="mb-6"
              rules={[
                {
                  validator: async (_, values) => {
                    const selectedItems = values?.filter((v) => v?.checked)
                    if (!selectedItems?.length) {
                      return Promise.reject(new Error("Please select at least one reviewer."));
                    }
                  },
                },
              ]}
            >
              {(fields) => (
                <List
                  header={
                    <div className="w-1/2 text-right">
                      <Search
                        onSearch={setSearch}
                        onClear={() => setSearch(null)}
                        placeholder="Search reviewer name"
                        className="w-full"
                        allowClear
                      />
                    </div>
                  }
                  footer={
                    loadMoreReviewers ? (
                      <Button
                        onClick={() => {
                          onLoadReviewers(revPage + 1);
                        }}
                        loading={loadMore}
                        block
                      >
                        Load more
                      </Button>
                    ) : null
                  }
                  dataSource={fields.filter((f) => {
                    if (search) {
                      return formInstance
                        .getFieldValue(["reviewers", f.name, "name"])
                        ?.toLowerCase()
                        ?.includes(search?.toLowerCase());
                    }
                    return f;
                  })}
                  renderItem={(field) => (
                    <List.Item>
                      <Space>
                        <Form.Item
                          valuePropName="checked"
                          name={[field.name, "checked"]}
                        >
                          <Checkbox />
                        </Form.Item>
                        <Text>
                          {formInstance.getFieldValue([
                            "reviewers",
                            field.name,
                            "name",
                          ])}
                        </Text>
                      </Space>
                    </List.Item>
                  )}
                />
              )}
            </Form.List>
          </div>

          <Flex align="center" justify="end" className="pt-6">
            <SubmitButton form={form} loading={loading}>
              Create
            </SubmitButton>
          </Flex>
        </div>
      )}
    </Form>
  );
};

export default PublicationForm;
