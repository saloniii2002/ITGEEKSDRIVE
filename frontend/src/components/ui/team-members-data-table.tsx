"use client";

import * as React from "react";
import {
  sortFn_datetime,
  type ColumnDef,
  type ColumnFiltersState,
  type SortingState,
  flexRender,
  tableFeatures,
  useTable,
  createSortedRowModel,
  rowSortingFeature,
  columnFilteringFeature,
  createFilteredRowModel,
  createPaginatedRowModel,
  rowPaginationFeature,
  rowSelectionFeature,
  columnVisibilityFeature,
  type ColumnVisibilityState,
} from "@tanstack/react-table";

const TABLE_FEATURES = tableFeatures({
  rowSortingFeature,
  columnFilteringFeature,
  rowPaginationFeature,
  rowSelectionFeature,
  columnVisibilityFeature,
  sortedRowModel: createSortedRowModel(),
  filteredRowModel: createFilteredRowModel(),
  paginatedRowModel: createPaginatedRowModel(),
  sortFns: {
    datetime: sortFn_datetime,
  },
});
import { toast } from "sonner";

import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Toaster } from "@/components/ui/sonner";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { IconPlaceholder } from "@/components/ui/team-members-data-table-utils/icon-placeholder";

type Status = "Active" | "Invited" | "Inactive";
type Role = "Admin" | "Editor" | "Viewer";

export type Member = {
  id: string;
  name: string;
  initials: string;
  avatar: string;
  email: string;
  status: Status;
  role: Role;
  joined: string;
};

const statusVariant: Record<Status, "default" | "secondary" | "outline"> = {
  Active: "default",
  Invited: "secondary",
  Inactive: "outline",
};

const roleClass: Record<Role, string> = {
  Admin: "text-foreground font-medium",
  Editor: "text-muted-foreground",
  Viewer: "text-muted-foreground",
};

const COLUMN_LABELS: Record<string, string> = {
  name: "Member",
  status: "Status",
  role: "Role",
  joined: "Joined",
};

export const defaultMembers: Member[] = [
  {
    id: "m-01",
    name: "Ada Lovelace",
    initials: "AL",
    avatar: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80",
    email: "ada@acme.io",
    status: "Active",
    role: "Admin",
    joined: "2026-06-12",
  },
  {
    id: "m-02",
    name: "Alan Turing",
    initials: "AT",
    avatar: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80",
    email: "alan@acme.io",
    status: "Active",
    role: "Editor",
    joined: "2026-06-10",
  },
  {
    id: "m-03",
    name: "Grace Hopper",
    initials: "GH",
    avatar: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150&auto=format&fit=crop&q=80",
    email: "grace@acme.io",
    status: "Invited",
    role: "Editor",
    joined: "2026-06-08",
  },
  {
    id: "m-04",
    name: "Linus Pauling",
    initials: "LP",
    avatar: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&auto=format&fit=crop&q=80",
    email: "linus@acme.io",
    status: "Inactive",
    role: "Viewer",
    joined: "2026-05-29",
  },
  {
    id: "m-05",
    name: "Katherine Johnson",
    initials: "KJ",
    avatar: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150&auto=format&fit=crop&q=80",
    email: "katherine@acme.io",
    status: "Active",
    role: "Viewer",
    joined: "2026-05-21",
  },
  {
    id: "m-06",
    name: "Edsger Dijkstra",
    initials: "ED",
    avatar: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=150&auto=format&fit=crop&q=80",
    email: "edsger@acme.io",
    status: "Active",
    role: "Admin",
    joined: "2026-05-18",
  },
];

const dateFmt = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "2-digit",
  year: "numeric",
});

function formatDate(value: string) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : dateFmt.format(parsed);
}

function SortIcon({ sorted }: { sorted: false | "asc" | "desc" }) {
  if (sorted === "asc")
    return (
      <IconPlaceholder
        lucide="ArrowUp"
        tabler="IconArrowUp"
        hugeicons="ArrowUpIcon"
        phosphor="ArrowUp"
        remixicon="RiArrowUpLine"
        className="size-3.5"
        aria-hidden="true"
      />
    );
  if (sorted === "desc")
    return (
      <IconPlaceholder
        lucide="ArrowDown"
        tabler="IconArrowDown"
        hugeicons="ArrowDownIcon"
        phosphor="ArrowDown"
        remixicon="RiArrowDownLine"
        className="size-3.5"
        aria-hidden="true"
      />
    );
  return (
    <IconPlaceholder
      lucide="ChevronsUpDown"
      tabler="IconArrowsVertical"
      hugeicons="ArrowUpDownIcon"
      phosphor="CaretUpDown"
      remixicon="RiExpandUpDownLine"
      className="size-3.5 text-muted-foreground/60"
      aria-hidden="true"
    />
  );
}

interface TableBlockProps {
  membersData?: Member[];
  onMembersChange?: (members: Member[]) => void;
  onProceed?: (selectedMembers: Member[]) => void;
}

export default function TableBlock({
  membersData,
  onMembersChange,
  onProceed,
}: TableBlockProps) {
  const [data, setData] = React.useState<Member[]>(
    membersData && membersData.length > 0 ? membersData : defaultMembers
  );

  React.useEffect(() => {
    if (membersData && membersData.length > 0) {
      setData(membersData);
    }
  }, [membersData]);

  const [sorting, setSorting] = React.useState<SortingState>([
    { id: "joined", desc: true },
  ]);
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>(
    [],
  );
  const [columnVisibility, setColumnVisibility] =
    React.useState<ColumnVisibilityState>({});
  const [rowSelection, setRowSelection] = React.useState({});
  const [newMemberName, setNewMemberName] = React.useState("");
  const [newMemberEmail, setNewMemberEmail] = React.useState("");

  const columns = React.useMemo<ColumnDef<typeof TABLE_FEATURES, Member>[]>(
    () => [
      {
        id: "select",
        enableSorting: false,
        enableHiding: false,
        header: ({ table }) => (
          <Checkbox
            checked={table.getIsAllPageRowsSelected()}
            indeterminate={
              table.getIsSomePageRowsSelected() &&
              !table.getIsAllPageRowsSelected()
            }
            onCheckedChange={(checked) =>
              table.toggleAllPageRowsSelected(checked === true)
            }
            aria-label="Select all members on this page"
          />
        ),
        cell: ({ row }) => (
          <Checkbox
            checked={row.getIsSelected()}
            onCheckedChange={(checked) => row.toggleSelected(checked === true)}
            aria-label={`Select ${row.original.name}`}
          />
        ),
      },
      {
        accessorKey: "name",
        header: ({ column }) => (
          <button
            type="button"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
            className="-mx-1 inline-flex items-center gap-1 rounded-md px-1 text-xs font-medium tracking-wide text-muted-foreground uppercase transition-colors hover:text-foreground"
          >
            Member
            <SortIcon sorted={column.getIsSorted()} />
          </button>
        ),
        filterFn: (row, _id, value: string) => {
          const q = value.toLowerCase();
          return (
            row.original.name.toLowerCase().includes(q) ||
            row.original.email.toLowerCase().includes(q)
          );
        },
        cell: ({ row }) => {
          const member = row.original;
          return (
            <div className="flex min-w-0 items-center gap-3">
              <Avatar className="size-8 shrink-0 border border-border">
                <AvatarImage
                  src={member.avatar}
                  alt={member.name}
                  className="object-cover"
                />
                <AvatarFallback className="text-xs">
                  {member.initials}
                </AvatarFallback>
              </Avatar>
              <div className="min-w-0">
                <p className="truncate text-sm leading-tight font-medium">
                  {member.name}
                </p>
                <p className="truncate text-xs text-muted-foreground">
                  {member.email}
                </p>
              </div>
            </div>
          );
        },
      },
      {
        accessorKey: "status",
        enableSorting: false,
        header: () => (
          <span className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
            Status
          </span>
        ),
        cell: ({ row }) => (
          <Badge
            variant={statusVariant[row.original.status]}
            className="text-xs"
          >
            {row.original.status}
          </Badge>
        ),
      },
      {
        accessorKey: "role",
        header: ({ column }) => (
          <button
            type="button"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
            className="-mx-1 inline-flex items-center gap-1 rounded-md px-1 text-xs font-medium tracking-wide text-muted-foreground uppercase transition-colors hover:text-foreground"
          >
            Role
            <SortIcon sorted={column.getIsSorted()} />
          </button>
        ),
        cell: ({ row }) => (
          <span className={cn("text-sm", roleClass[row.original.role])}>
            {row.original.role}
          </span>
        ),
      },
      {
        accessorKey: "joined",
        sortFn: "datetime",
        header: ({ column }) => (
          <button
            type="button"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
            className="-mx-1 ml-auto inline-flex items-center gap-1 rounded-md px-1 text-xs font-medium tracking-wide text-muted-foreground uppercase transition-colors hover:text-foreground"
          >
            Joined
            <SortIcon sorted={column.getIsSorted()} />
          </button>
        ),
        cell: ({ row }) => (
          <span className="block text-right text-xs text-muted-foreground tabular-nums">
            {formatDate(row.original.joined)}
          </span>
        ),
      },
      {
        id: "actions",
        enableSorting: false,
        enableHiding: false,
        header: () => <span className="sr-only">Actions</span>,
        cell: ({ row }) => (
          <div className="flex justify-end">
            <DropdownMenu>
              <DropdownMenuTrigger
                render={
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label={`Actions for ${row.original.name}`}
                  >
                    <IconPlaceholder
                      lucide="Ellipsis"
                      tabler="IconDots"
                      hugeicons="MoreHorizontalIcon"
                      phosphor="DotsThree"
                      remixicon="RiMoreLine"
                      className="size-4"
                      aria-hidden="true"
                    />
                  </Button>
                }
              />
              <DropdownMenuContent align="end" className="w-40">
                <DropdownMenuItem
                  onClick={() =>
                    toast("Profile", {
                      description: `Viewing profile for ${row.original.name}`,
                    })
                  }
                >
                  <IconPlaceholder
                    lucide="User"
                    tabler="IconUser"
                    hugeicons="UserIcon"
                    phosphor="User"
                    remixicon="RiUserLine"
                    aria-hidden="true"
                  />
                  View Profile
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  variant="destructive"
                  onClick={() => {
                    const idToRemove = row.original.id;
                    const updated = data.filter((m) => m.id !== idToRemove);
                    setData(updated);
                    onMembersChange?.(updated);
                    toast("Member removed", {
                      description: `${row.original.name} was removed.`,
                    });
                  }}
                >
                  <IconPlaceholder
                    lucide="Trash"
                    tabler="IconTrash"
                    hugeicons="Delete02Icon"
                    phosphor="Trash"
                    remixicon="RiDeleteBinLine"
                    aria-hidden="true"
                  />
                  Remove
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        ),
      },
    ],
    [data, onMembersChange],
  );

  const table = useTable({
    features: TABLE_FEATURES,
    data,
    columns,
    getRowId: (row) => row.id,
    state: { sorting, columnFilters, columnVisibility, rowSelection },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,
    initialState: { pagination: { pageIndex: 0, pageSize: 6 } },
  });

  const nameFilter =
    (table.getColumn("name")?.getFilterValue() as string) ?? "";
  const selectedCount = table.getFilteredSelectedRowModel().rows.length;
  const totalCount = table.getFilteredRowModel().rows.length;
  const pageCount = table.getPageCount();

  function handleRemove() {
    const selectedIds = new Set(
      table.getFilteredSelectedRowModel().rows.map((row) => row.id),
    );
    const updated = data.filter((row) => !selectedIds.has(row.id));
    setData(updated);
    onMembersChange?.(updated);
    table.resetRowSelection();
    toast("Members removed", {
      description: `${selectedIds.size} ${
        selectedIds.size === 1 ? "member" : "members"
      } removed from the list.`,
    });
  }

  function handleAddMember() {
    if (!newMemberName.trim()) {
      toast.error("Please enter a member name");
      return;
    }
    const initials = newMemberName
      .trim()
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);

    const newM: Member = {
      id: `m-${Date.now()}`,
      name: newMemberName.trim(),
      initials: initials || "MB",
      avatar: `https://images.unsplash.com/photo-${1534528741775 + Math.floor(Math.random() * 500)}?w=150&auto=format&fit=crop&q=80`,
      email: newMemberEmail.trim() || `${newMemberName.toLowerCase().replace(/\s+/g, "")}@example.com`,
      status: "Active",
      role: "Editor",
      joined: new Date().toISOString().split("T")[0],
    };

    const updated = [newM, ...data];
    setData(updated);
    onMembersChange?.(updated);
    setNewMemberName("");
    setNewMemberEmail("");
    toast.success("Member added", {
      description: `${newM.name} added to dinner group.`,
    });
  }

  return (
    <section className="flex w-full justify-center bg-card/60 rounded-xl p-4 text-foreground border border-border">
      <div className="w-full">
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-md border border-border bg-card text-muted-foreground">
              <IconPlaceholder
                lucide="UserCog"
                tabler="IconShield"
                hugeicons="ShieldUserIcon"
                phosphor="Shield"
                remixicon="RiShieldUserLine"
                className="size-4"
                aria-hidden="true"
              />
            </div>
            <div>
              <h1 className="font-heading text-lg leading-tight font-semibold tracking-tight">
                Bill Diners & Team Members
              </h1>
              <p className="text-sm text-muted-foreground">
                {data.length} diners ready to split the bill
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="relative">
              <IconPlaceholder
                lucide="Search"
                tabler="IconSearch"
                hugeicons="SearchIcon"
                phosphor="MagnifyingGlass"
                remixicon="RiSearchLine"
                className="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground"
                aria-hidden="true"
              />
              <Input
                type="search"
                value={nameFilter}
                onChange={(event) =>
                  table.getColumn("name")?.setFilterValue(event.target.value)
                }
                placeholder="Search members..."
                className="h-8 w-44 pl-8 text-sm"
                aria-label="Search members by name or email"
              />
            </div>
            <DropdownMenu>
              <DropdownMenuTrigger
                render={
                  <Button
                    variant="outline"
                    size="sm"
                    aria-label="Toggle columns"
                  >
                    <IconPlaceholder
                      lucide="Columns"
                      tabler="IconColumns"
                      hugeicons="LayoutLeftIcon"
                      phosphor="Columns"
                      remixicon="RiLayoutColumnLine"
                      className="size-3.5"
                      aria-hidden="true"
                    />
                    View
                  </Button>
                }
              />
              <DropdownMenuContent align="end" className="w-40">
                <DropdownMenuGroup>
                  <DropdownMenuLabel>Toggle Columns</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  {table
                    .getAllColumns()
                    .filter((column) => column.getCanHide())
                    .map((column) => (
                      <DropdownMenuCheckboxItem
                        key={column.id}
                        checked={column.getIsVisible()}
                        onCheckedChange={(checked) =>
                          column.toggleVisibility(checked === true)
                        }
                        closeOnClick={false}
                      >
                        {COLUMN_LABELS[column.id] ?? column.id}
                      </DropdownMenuCheckboxItem>
                    ))}
                </DropdownMenuGroup>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        {/* Quick Add Member Input Bar */}
        <div className="mb-4 flex flex-wrap items-center gap-2 p-3 bg-muted/30 border border-border rounded-lg">
          <Input
            placeholder="Diner Name (e.g. Alice)"
            value={newMemberName}
            onChange={(e) => setNewMemberName(e.target.value)}
            className="h-8 flex-1 min-w-[140px] text-sm"
          />
          <Input
            placeholder="Email / Phone (Optional)"
            value={newMemberEmail}
            onChange={(e) => setNewMemberEmail(e.target.value)}
            className="h-8 flex-1 min-w-[140px] text-sm"
          />
          <Button size="sm" onClick={handleAddMember} className="h-8">
            <IconPlaceholder
              lucide="Plus"
              tabler="IconPlus"
              hugeicons="Add01Icon"
              phosphor="Plus"
              remixicon="RiAddLine"
              className="mr-1 size-3.5"
              aria-hidden="true"
            />
            Add Diner
          </Button>
        </div>

        {selectedCount > 0 && (
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-muted/40 px-4 py-2.5">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-foreground tabular-nums">
                {selectedCount} Selected
              </span>
              <Button
                variant="ghost"
                size="xs"
                className="text-muted-foreground hover:text-foreground"
                onClick={() => table.resetRowSelection()}
              >
                Clear
              </Button>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="text-destructive hover:text-destructive"
                onClick={handleRemove}
              >
                <IconPlaceholder
                  lucide="Trash"
                  tabler="IconTrash"
                  hugeicons="Delete02Icon"
                  phosphor="Trash"
                  remixicon="RiDeleteBinLine"
                  className="size-3.5"
                  aria-hidden="true"
                />
                Remove Selected
              </Button>
            </div>
          </div>
        )}

        <div className="overflow-hidden rounded-xl border border-border bg-card">
          <Table>
            <TableHeader>
              {table.getHeaderGroups().map((headerGroup) => (
                <TableRow
                  key={headerGroup.id}
                  className="border-b border-border bg-muted/40 hover:bg-muted/40"
                >
                  {headerGroup.headers.map((header) => (
                    <TableHead
                      key={header.id}
                      className={cn(
                        "h-9",
                        header.column.id === "select" && "w-10 pl-4",
                        header.column.id === "name" && "pl-1",
                        header.column.id === "joined" && "text-right",
                        header.column.id === "actions" && "w-10 pr-4",
                      )}
                    >
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext(),
                          )}
                    </TableHead>
                  ))}
                </TableRow>
              ))}
            </TableHeader>
            <TableBody>
              {table.getRowModel().rows.length ? (
                table.getRowModel().rows.map((row) => (
                  <TableRow
                    key={row.id}
                    data-state={row.getIsSelected() ? "selected" : undefined}
                    className="border-b border-border transition-colors duration-100 last:border-b-0 hover:bg-muted/30"
                  >
                    {row.getVisibleCells().map((cell) => (
                      <TableCell
                        key={cell.id}
                        className={cn(
                          "py-2.5",
                          cell.column.id === "select" && "pl-4",
                          cell.column.id === "name" && "pl-1",
                          cell.column.id === "actions" && "pr-4",
                        )}
                      >
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext(),
                        )}
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              ) : (
                <TableRow className="hover:bg-transparent">
                  <TableCell
                    colSpan={columns.length}
                    className="h-24 text-center text-sm text-muted-foreground"
                  >
                    No members match your search.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>

          <div className="flex items-center justify-between gap-4 border-t border-border bg-muted/20 px-4 py-2.5">
            <p className="text-xs text-muted-foreground">
              <span className="font-medium text-foreground">{totalCount}</span>{" "}
              {totalCount === 1 ? "Diner" : "Diners"}
            </p>
            <div className="flex items-center gap-1.5">
              <Button
                variant="outline"
                size="icon"
                className="size-7"
                onClick={() => table.previousPage()}
                disabled={!table.getCanPreviousPage()}
                aria-label="Previous page"
              >
                <IconPlaceholder
                  lucide="ChevronLeft"
                  tabler="IconChevronLeft"
                  hugeicons="ArrowLeft01Icon"
                  phosphor="CaretLeft"
                  remixicon="RiArrowLeftSLine"
                  className="size-3.5"
                  aria-hidden="true"
                />
              </Button>
              <span className="px-1 text-xs text-muted-foreground tabular-nums">
                Page {table.state.pagination.pageIndex + 1} of{" "}
                {Math.max(pageCount, 1)}
              </span>
              <Button
                variant="outline"
                size="icon"
                className="size-7"
                onClick={() => table.nextPage()}
                disabled={!table.getCanNextPage()}
                aria-label="Next page"
              >
                <IconPlaceholder
                  lucide="ChevronRight"
                  tabler="IconChevronRight"
                  hugeicons="ArrowRight01Icon"
                  phosphor="CaretRight"
                  remixicon="RiArrowRightSLine"
                  className="size-3.5"
                  aria-hidden="true"
                />
              </Button>
            </div>
          </div>
        </div>

        {onProceed && (
          <div className="mt-4 flex justify-end">
            <Button
              onClick={() => onProceed(data)}
              className="bg-primary hover:bg-primary/90"
              disabled={data.length === 0}
            >
              Continue with {data.length} Diners
            </Button>
          </div>
        )}
      </div>
      <Toaster />
    </section>
  );
}
