import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';

/** 按学段与年级自然顺序排序（一年级→九年级→高一→高三→高中），其余按字典序。 */
const LEVEL_ORDER = [
  '一年级', '二年级', '三年级', '四年级', '五年级', '六年级',
  '七年级', '八年级', '九年级', '高一', '高二', '高三', '高中', '小学', '初中',
];
function sortLevels(levels: string[]): string[] {
  return [...levels].sort((a, b) => {
    const ia = LEVEL_ORDER.indexOf(a);
    const ib = LEVEL_ORDER.indexOf(b);
    if (ia >= 0 && ib >= 0) return ia - ib;
    if (ia >= 0) return -1;
    if (ib >= 0) return 1;
    return a.localeCompare(b, 'zh-Hans-CN');
  });
}

export type BankFilterState = {
  bank: string;
  type: string;
  star: string;
  subject: string;
  level: string;
  wrong: string;
  sort: string;
  showAll: boolean;
};

interface FilterSheetProps {
  open: boolean;
  onClose: () => void;
  banks: string[];
  subjects: string[];
  levels: string[];
  filters: BankFilterState;
  onChange: (key: keyof BankFilterState, value: string | boolean) => void;
  onReset: () => void;
}

/** 题库筛选侧栏：筛选条件集中在一处，不再占用列表上方一行行铺开。 */
export function FilterSheet({
  open,
  onClose,
  banks,
  subjects,
  levels,
  filters,
  onChange,
  onReset,
}: FilterSheetProps) {
  const orderedLevels = sortLevels(levels);
  const activeCount = [
    filters.bank !== 'all',
    filters.type !== 'all',
    filters.star !== 'all',
    filters.subject !== 'all',
    filters.level !== 'all',
    filters.wrong !== 'all',
    filters.sort !== 'default',
    filters.showAll,
  ].filter(Boolean).length;

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent side="right" className="flex w-full flex-col gap-0 p-0 sm:max-w-[400px]">
        <SheetHeader className="border-b px-5 py-4 pe-12">
          <SheetTitle>筛选题目{activeCount > 0 ? `（已选 ${activeCount} 项）` : ''}</SheetTitle>
          <SheetDescription>按条件过滤题库内容</SheetDescription>
        </SheetHeader>

        <div className="flex-1 space-y-4 overflow-y-auto px-5 py-5">
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-foreground">题库</label>
            <Select value={filters.bank} onValueChange={v => onChange('bank', v)}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部题库</SelectItem>
                {banks.map(b => (
                  <SelectItem key={b} value={b}>
                    {b}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-3.5">
            {subjects.length > 0 && (
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-foreground">科目</label>
                <Select value={filters.subject} onValueChange={v => onChange('subject', v)}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">全部科目</SelectItem>
                    {subjects.map(s => (
                      <SelectItem key={s} value={s}>
                        {s}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {orderedLevels.length > 0 && (
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-foreground">年级</label>
                <Select value={filters.level} onValueChange={v => onChange('level', v)}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">全部年级</SelectItem>
                    {orderedLevels.map(l => (
                      <SelectItem key={l} value={l}>
                        {l}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="space-y-1.5">
              <label className="text-sm font-medium text-foreground">题型</label>
              <Select value={filters.type} onValueChange={v => onChange('type', v)}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部题型</SelectItem>
                  <SelectItem value="single">单选</SelectItem>
                  <SelectItem value="multiple">多选</SelectItem>
                  <SelectItem value="boolean">判断</SelectItem>
                  <SelectItem value="text">填空</SelectItem>
                  <SelectItem value="subjective">主观题</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium text-foreground">难度</label>
              <Select value={filters.star} onValueChange={v => onChange('star', v)}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部难度</SelectItem>
                  {[1, 2, 3, 4, 5].map(n => (
                    <SelectItem key={n} value={String(n)}>
                      {'★'.repeat(n)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium text-foreground">错题</label>
              <Select value={filters.wrong} onValueChange={v => onChange('wrong', v)}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部题目</SelectItem>
                  <SelectItem value="wrong">只看错题</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium text-foreground">排序</label>
              <Select value={filters.sort} onValueChange={v => onChange('sort', v)}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="default">默认</SelectItem>
                  <SelectItem value="diff">按难度</SelectItem>
                  <SelectItem value="type">按题型</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex items-center justify-between rounded-lg border px-3.5 py-3">
            <label className="text-sm font-medium text-foreground">显示已暂停题目</label>
            <Switch checked={filters.showAll} onCheckedChange={v => onChange('showAll', v)} />
          </div>
        </div>

        <SheetFooter className="flex-row gap-2.5 border-t px-5 py-3.5">
          <Button variant="outline" className="flex-1" disabled={activeCount === 0} onClick={onReset}>
            清除筛选
          </Button>
          <Button className="flex-1" onClick={onClose}>
            完成
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
